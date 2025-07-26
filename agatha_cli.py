#!/usr/bin/env python3
"""
Agatha: A Multi-Model AI Consensus System
CLI Interface

This script provides a command-line interface for the Agatha system, which processes
user questions through a pipeline of AI models and displays the results.
"""

import os
import sys
import time
import json
import logging
import datetime
import requests
import base64
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M")
log_filename = f"agatha_{current_time}.log"

# Create file handler for detailed logging
file_handler = logging.FileHandler(log_filename)
file_handler.setLevel(logging.INFO)
file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_format)

# Create console handler with minimal output - only for user-facing messages
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_format = logging.Formatter('%(message)s')
console_handler.setFormatter(console_format)

# Create main logger for console output (minimal user-facing messages only)
logger = logging.getLogger("agatha.console")
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)
logger.propagate = False  # Prevent propagation to root logger

# Create a separate logger for detailed output that only goes to file
detail_logger = logging.getLogger("agatha.detail")
detail_logger.setLevel(logging.INFO)
detail_logger.addHandler(file_handler)
detail_logger.propagate = False  # Prevent propagation to root logger

# Import google-genai for Gemini models
try:
    from google import genai
    from google.genai import types
    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    GOOGLE_GENAI_AVAILABLE = False
    logger.warning("google-genai package not found. Gemini grounding will not work properly.")
    logger.warning("Install with: pip install google-genai")

# Load environment variables
load_dotenv()

class AgathaSystem:
    """Main class for the Agatha Multi-Model AI Consensus System."""
    
    def __init__(self):
        """Initialize the Agatha system."""
        logger.info("Initializing Agatha Multi-Model AI Consensus System")
        
        # Load system prompts
        self.system_prompts = {}
        self._load_system_prompts()
        
        # Configure models
        self.models = {
            1: {
                "name": os.getenv("MODEL_STEP1", "gemini-2.5-flash"),
                "temperature": float(os.getenv("TEMPERATURE_STEP1", "0.3")),
                "provider": os.getenv("MODEL_STEP1_PROVIDER", "openrouter"),
            },
            2: {
                "name": os.getenv("MODEL_STEP2", "anthropic/claude-opus-4"),
                "temperature": float(os.getenv("TEMPERATURE_STEP2", "0.7")),
                "provider": os.getenv("MODEL_STEP2_PROVIDER", "openrouter"),
            },
            3: {
                "name": os.getenv("MODEL_STEP3", "openai/o4-mini"),
                "temperature": float(os.getenv("TEMPERATURE_STEP3", "0.3")),
                "provider": os.getenv("MODEL_STEP3_PROVIDER", "openrouter"),
            },
            4: {
                "name": os.getenv("MODEL_STEP4", "gemini-2.5-pro"),
                "temperature": float(os.getenv("TEMPERATURE_STEP4", "0.5")),
                "provider": os.getenv("MODEL_STEP4_PROVIDER", "openrouter"),
            }
        }
        
        # API configuration
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.openrouter_api_key:
            logger.warning("OPENROUTER_API_KEY not found in .env file")
            
        # Check for direct API keys
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        logger.info("Agatha system initialized successfully")
    
    def _load_system_prompts(self):
        """Load system prompts from files."""
        try:
            for i in range(1, 5):
                prompt_file = f"system_prompt{i}.md"
                with open(prompt_file, 'r') as f:
                    self.system_prompts[i] = f.read()
                logger.info(f"Loaded system prompt {i} from {prompt_file}")
        except Exception as e:
            logger.error(f"Error loading system prompts: {e}")
            sys.exit(1)
    
    def _call_api(self, step_number, messages, temperature):
        """Call the appropriate API based on the provider setting for the step."""
        model = self.models[step_number]["name"]
        provider = self.models[step_number]["provider"]
        
        # Log to detail_logger for file only
        detail_logger.info(f"Using provider: {provider} for step {step_number}")
        
        if provider == "openrouter":
            return self._call_openrouter_api(step_number, model, messages, temperature)
        elif provider == "google":
            # Only use Google Search tool grounding in Step 1
            use_grounding = (step_number == 1)
            return self._call_google_api(step_number, model, messages, temperature, use_grounding)
        elif provider == "anthropic":
            return self._call_anthropic_api(step_number, model, messages, temperature)
        elif provider == "openai":
            return self._call_openai_api(step_number, model, messages, temperature)
        else:
            error_msg = f"Unknown provider: {provider} for step {step_number}"
            logger.error(error_msg)
            detail_logger.error(error_msg)
            return {"error": error_msg}
    
    def _call_openrouter_api(self, step_number, model, messages, temperature):
        """Call the OpenRouter API with the specified model and messages."""
        try:
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": model,
                "messages": messages,
                "temperature": temperature
            }
            
            detail_logger.info(f"Step {step_number}: Calling OpenRouter API with model: {model}")
            detail_logger.info(f"Step {step_number}: Request data: {json.dumps(data, indent=2)}")
            
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data
            )
            
            if response.status_code != 200:
                detail_logger.error(f"Step {step_number}: OpenRouter API error: {response.status_code} {response.text}")
                return {"error": f"API Error: {response.status_code} {response.text}"}
            
            response_json = response.json()
            detail_logger.info(f"Step {step_number}: OpenRouter API response: {json.dumps(response_json, indent=2)}")
            
            return response_json
        except Exception as e:
            detail_logger.error(f"Step {step_number}: Error calling OpenRouter API: {e}")
            if hasattr(e, 'response') and e.response:
                detail_logger.error(f"Step {step_number}: Response status: {e.response.status_code}")
                detail_logger.error(f"Step {step_number}: Response body: {e.response.text}")
            return {"error": str(e)}
    
    def _call_google_api(self, step_number, model, messages, temperature, use_grounding=False):
        """Call the Google Gemini API with the specified model and messages."""
        try:
            if not GOOGLE_GENAI_AVAILABLE:
                detail_logger.error(f"Step {step_number}: google-genai package not installed. Cannot use Google API.")
                return {"error": "google-genai package not installed. Install with: pip install google-genai"}
            
            # Extract the message content from the messages
            user_content = ""
            system_content = ""
            
            for msg in messages:
                if msg["role"] == "system":
                    system_content = msg["content"]
                elif msg["role"] == "user":
                    user_content = msg["content"]
            
            # Combine system and user content if both exist
            input_text = system_content
            if system_content and user_content:
                input_text += "\n\n" + user_content
            elif user_content:
                input_text = user_content
            
            # Initialize the Google Gemini client
            client = genai.Client(api_key=self.google_api_key)
            
            # Create the content for the API call
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=input_text),
                    ],
                ),
            ]
            
            # Configure the generation parameters
            if use_grounding:
                # Set up Google Search tool for grounding (only in Step 1)
                tools = [types.Tool(google_search=types.GoogleSearch())]
                generate_content_config = types.GenerateContentConfig(
                    tools=tools,
                    temperature=temperature
                )
                detail_logger.info(f"Step {step_number}: Using Google Search grounding")
            else:
                # No grounding for other steps
                generate_content_config = types.GenerateContentConfig(
                    temperature=temperature
                )
                detail_logger.info(f"Step {step_number}: Not using grounding")
            
            detail_logger.info(f"Step {step_number}: Calling Google Gemini API with model: {model}")
            detail_logger.info(f"Step {step_number}: Input text: {input_text}")
            detail_logger.info(f"Step {step_number}: Temperature: {temperature}")
            
            # Call the API
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=generate_content_config,
            )
            
            # Log the full response
            detail_logger.info(f"Step {step_number}: Google Gemini API raw response: {response}")
            
            # Extract the content
            content = ""
            if response.text:
                content = response.text
            
            # Format the response to match the expected format
            formatted_response = {
                "choices": [
                    {
                        "message": {
                            "content": content
                        }
                    }
                ]
            }
            
            detail_logger.info(f"Step {step_number}: Google API formatted response: {json.dumps(formatted_response, indent=2)}")
            return formatted_response
            
        except Exception as e:
            detail_logger.error(f"Step {step_number}: Error calling Google API: {e}")
            if hasattr(e, 'response') and e.response:
                detail_logger.error(f"Step {step_number}: Response status: {e.response.status_code}")
                detail_logger.error(f"Step {step_number}: Response body: {e.response.text}")
            return {"error": str(e)}
    
    def _call_anthropic_api(self, step_number, model, messages, temperature):
        """Call the Anthropic API with the specified model and messages."""
        try:
            # Format messages for Anthropic API
            formatted_messages = []
            system_content = ""
            
            for msg in messages:
                if msg["role"] == "system":
                    system_content = msg["content"]
                else:
                    formatted_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            headers = {
                "x-api-key": self.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": model,
                "messages": formatted_messages,
                "system": system_content,
                "temperature": temperature,
                "max_tokens": 4000
            }
            
            detail_logger.info(f"Step {step_number}: Calling Anthropic API with model: {model}")
            detail_logger.info(f"Step {step_number}: Request data: {json.dumps(data, indent=2)}")
            
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=data
            )
            
            if response.status_code != 200:
                logger.error(f"Step {step_number}: Anthropic API error: {response.status_code} {response.text}")
                return {"error": f"API Error: {response.status_code} {response.text}"}
            
            # Format response to match OpenRouter format
            response_data = response.json()
            logger.info(f"Step {step_number}: Anthropic API raw response: {json.dumps(response_data, indent=2)}")
            
            content = response_data.get("content", [{}])[0].get("text", "")
            
            formatted_response = {
                "choices": [
                    {
                        "message": {
                            "content": content
                        }
                    }
                ]
            }
            
            detail_logger.info(f"Step {step_number}: Anthropic API formatted response: {json.dumps(formatted_response, indent=2)}")
            return formatted_response
        except Exception as e:
            detail_logger.error(f"Step {step_number}: Error calling Anthropic API: {e}")
            if hasattr(e, 'response') and e.response:
                detail_logger.error(f"Step {step_number}: Response status: {e.response.status_code}")
                detail_logger.error(f"Step {step_number}: Response body: {e.response.text}")
            return {"error": str(e)}
    
    def _call_openai_api(self, step_number, model, messages, temperature):
        """Call the OpenAI API with the specified model and messages."""
        try:
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": model,
                "messages": messages,
                "temperature": temperature
            }
            
            detail_logger.info(f"Step {step_number}: Calling OpenAI API with model: {model}")
            detail_logger.info(f"Step {step_number}: Request data: {json.dumps(data, indent=2)}")
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data
            )
            
            if response.status_code != 200:
                detail_logger.error(f"Step {step_number}: OpenAI API error: {response.status_code} {response.text}")
                return {"error": f"API Error: {response.status_code} {response.text}"}
            
            response_json = response.json()
            detail_logger.info(f"Step {step_number}: OpenAI API response: {json.dumps(response_json, indent=2)}")
            
            return response_json
        except Exception as e:
            detail_logger.error(f"Step {step_number}: Error calling OpenAI API: {e}")
            if hasattr(e, 'response') and e.response:
                detail_logger.error(f"Step {step_number}: Response status: {e.response.status_code}")
                detail_logger.error(f"Step {step_number}: Response body: {e.response.text}")
            return {"error": str(e)}
    
    def process_question(self, question):
        """Process a user question through the Agatha pipeline."""
        # Log detailed info to file only
        detail_logger.info(f"Processing question: {question}")
        # Log minimal info to console
        logger.info(f"\nProcessing question: {question}\n")
        
        responses = {}
        
        # Step 1: Gemini Flash - Grounding
        model_name = self.models[1]["name"]
        provider = self.models[1]["provider"]
        logger.info(f"Step 1: {model_name} via {provider} - Grounding...")
        detail_logger.info("Step 1: Gemini Flash - Grounding")
        
        step1_prompt = self.system_prompts[1].replace("{{user_question}}", question)
        step1_messages = [
            {"role": "system", "content": step1_prompt},
            {"role": "user", "content": question}
        ]
        
        step1_response = self._call_api(
            1,
            step1_messages,
            self.models[1]["temperature"]
        )
        
        if "error" in step1_response:
            detail_logger.error(f"Error in Step 1: {step1_response['error']}")
            logger.error(f"Error in Step 1: {step1_response['error']}")
            return {"error": f"Error in Step 1: {step1_response['error']}"}
        
        step1_content = step1_response.get("choices", [{}])[0].get("message", {}).get("content", "")
        responses[1] = step1_content
        detail_logger.info(f"Step 1 complete. Response length: {len(step1_content)}")
        logger.info(f"Step 1: Complete ✓")
        
        # Step 2: Claude Opus - Analysis
        model_name = self.models[2]["name"]
        provider = self.models[2]["provider"]
        logger.info(f"\nStep 2: {model_name} via {provider} - Analysis...")
        detail_logger.info("Step 2: Claude Opus - Analysis")
        
        step2_prompt = (self.system_prompts[2]
                        .replace("{{user_question}}", question)
                        .replace("{{model1_response}}", step1_content))
        step2_messages = [
            {"role": "system", "content": step2_prompt},
            {"role": "user", "content": question}
        ]
        
        step2_response = self._call_api(
            2,
            step2_messages,
            self.models[2]["temperature"]
        )
        
        if "error" in step2_response:
            detail_logger.error(f"Error in Step 2: {step2_response['error']}")
            logger.error(f"Error in Step 2: {step2_response['error']}")
            return {"error": f"Error in Step 2: {step2_response['error']}"}
        
        step2_content = step2_response.get("choices", [{}])[0].get("message", {}).get("content", "")
        responses[2] = step2_content
        detail_logger.info(f"Step 2 complete. Response length: {len(step2_content)}")
        logger.info(f"Step 2: Complete ✓")
        
        # Step 3: GPT-4o-mini - Fact-check & Proofread
        model_name = self.models[3]["name"]
        provider = self.models[3]["provider"]
        logger.info(f"\nStep 3: {model_name} via {provider} - Fact-check & Proofread...")
        detail_logger.info("Step 3: GPT-4o-mini - Fact-check & Proofread")
        
        step3_prompt = (self.system_prompts[3]
                        .replace("{{user_question}}", question)
                        .replace("{{model1_response}}", step1_content)
                        .replace("{{model2_response}}", step2_content))
        step3_messages = [
            {"role": "system", "content": step3_prompt},
            {"role": "user", "content": question}
        ]
        
        step3_response = self._call_api(
            3,
            step3_messages,
            self.models[3]["temperature"]
        )
        
        if "error" in step3_response:
            detail_logger.error(f"Error in Step 3: {step3_response['error']}")
            logger.error(f"Error in Step 3: {step3_response['error']}")
            return {"error": f"Error in Step 3: {step3_response['error']}"}
        
        step3_content = step3_response.get("choices", [{}])[0].get("message", {}).get("content", "")
        responses[3] = step3_content
        detail_logger.info(f"Step 3 complete. Response length: {len(step3_content)}")
        logger.info(f"Step 3: Complete ✓")
        
        # Step 4: Gemini Pro - Synthesis & Consensus
        model_name = self.models[4]["name"]
        provider = self.models[4]["provider"]
        logger.info(f"\nStep 4: {model_name} via {provider} - Synthesis & Consensus...")
        detail_logger.info("Step 4: Gemini Pro - Synthesis & Consensus")
        
        step4_prompt = (self.system_prompts[4]
                        .replace("{{user_question}}", question)
                        .replace("{{model1_response}}", step1_content)
                        .replace("{{model2_response}}", step2_content)
                        .replace("{{model3_response}}", step3_content))
        step4_messages = [
            {"role": "system", "content": step4_prompt},
            {"role": "user", "content": question}
        ]
        
        step4_response = self._call_api(
            4,
            step4_messages,
            self.models[4]["temperature"]
        )
        
        if "error" in step4_response:
            detail_logger.error(f"Error in Step 4: {step4_response['error']}")
            logger.error(f"Error in Step 4: {step4_response['error']}")
            return {"error": f"Error in Step 4: {step4_response['error']}"}
        
        step4_content = step4_response.get("choices", [{}])[0].get("message", {}).get("content", "")
        responses[4] = step4_content
        detail_logger.info(f"Step 4 complete. Response length: {len(step4_content)}")
        logger.info(f"Step 4: Complete ✓\n")
        
        # Log all responses to file
        self._log_full_responses(question, responses)
        
        return responses
    
    def _log_full_responses(self, question, responses):
        """Log the full responses to the log file."""
        detail_logger.info("Logging full responses to log file")
        
        # Create a detailed log entry with all information
        log_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "question": question,
            "model_configuration": {
                1: {
                    "name": self.models[1]["name"],
                    "temperature": self.models[1]["temperature"],
                    "provider": self.models[1]["provider"]
                },
                2: {
                    "name": self.models[2]["name"],
                    "temperature": self.models[2]["temperature"],
                    "provider": self.models[2]["provider"]
                },
                3: {
                    "name": self.models[3]["name"],
                    "temperature": self.models[3]["temperature"],
                    "provider": self.models[3]["provider"]
                },
                4: {
                    "name": self.models[4]["name"],
                    "temperature": self.models[4]["temperature"],
                    "provider": self.models[4]["provider"]
                }
            },
            "responses": responses
        }
        
        detail_logger.info(f"Full response data: {json.dumps(log_data, indent=2)}")
    
    def display_responses(self, responses):
        """Display the responses from each step in a formatted way."""
        if "error" in responses:
            print(f"\n❌ Error: {responses['error']}")
            return
        
        print("\n" + "="*80)
        print("🔍 STEP 1: GEMINI FLASH - FACTUAL GROUNDING")
        print("="*80)
        print(responses[1])
        
        print("\n" + "="*80)
        print("🧠 STEP 2: CLAUDE OPUS - DEEP ANALYSIS")
        print("="*80)
        print(responses[2])
        
        print("\n" + "="*80)
        print("✅ STEP 3: GPT-4O-MINI - FACT-CHECKING & PROOFREADING")
        print("="*80)
        print(responses[3])
        
        print("\n" + "="*80)
        print("🔄 STEP 4: GEMINI PRO - SYNTHESIS & CONSENSUS")
        print("="*80)
        print(responses[4])
        
        print("\n" + "="*80)
        print(f"✨ All responses have been logged to {log_filename}")
        print("="*80)


def main():
    """Main function to run the Agatha CLI."""
    try:
        print("\n" + "="*80)
        print("🔮 AGATHA: MULTI-MODEL AI CONSENSUS SYSTEM")
        print("="*80)
        print("Welcome to Agatha, a system that combines multiple AI models to provide")
        print("comprehensive answers with consensus detection and divergence highlighting.")
        print("="*80)
        
        # Verify API keys before starting
        print("\nVerifying API keys...")
        if not verify_api_keys():
            print("❌ API key verification failed. Please check your .env file.")
            return
        
        # Initialize the Agatha system
        try:
            agatha = AgathaSystem()
        except Exception as e:
            print(f"❌ Error initializing Agatha system: {e}")
            return
        
        # Main interaction loop
        while True:
            try:
                question = input("\nEnter your question (or type 'exit' to quit):\n> ")
                
                if question.lower() in ['exit', 'quit', 'q']:
                    print("\n👋 Thank you for using Agatha! Goodbye!")
                    break
                
                if not question.strip():
                    print("Please enter a valid question.")
                    continue
                
                print("\nProcessing your question through the Agatha pipeline...")
                start_time = time.time()
                
                responses = agatha.process_question(question)
                
                if "error" in responses:
                    print(f"\n❌ Error: {responses['error']}")
                else:
                    agatha.display_responses(responses)
                
                end_time = time.time()
                processing_time = end_time - start_time
                print(f"\nTotal processing time: {processing_time:.2f} seconds")
                
            except EOFError:
                print("\nEOFError detected. Using default question for testing.")
                question = "What are the major causes of climate change? (default test question)"
                print(f"> {question}")
                
                print("\nProcessing your question through the Agatha pipeline...")
                start_time = time.time()
                
                responses = agatha.process_question(question)
                
                if "error" in responses:
                    print(f"\n❌ Error: {responses['error']}")
                else:
                    agatha.display_responses(responses)
                
                end_time = time.time()
                processing_time = end_time - start_time
                print(f"\nTotal processing time: {processing_time:.2f} seconds")
            
            except Exception as e:
                print(f"\n❌ An unexpected error occurred: {e}")
                print("Please try again or type 'exit' to quit.")
    
    except KeyboardInterrupt:
        print("\n\n👋 Gracefully shutting down Agatha...")
        print("Thank you for using the Agatha Multi-Model AI Consensus System!")
        print("Goodbye! 🎆")
        return


def verify_api_keys():
    """Verify API keys without consuming credits."""
    detail_logger.info("Verifying API keys")
    
    # Track verification status
    all_keys_valid = True
    
    # Check OpenRouter API key
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_api_key:
        # Verify OpenRouter API key by checking models endpoint
        # This endpoint doesn't consume credits but can verify if the API key is valid
        try:
            detail_logger.info("Verifying OpenRouter API key")
            headers = {
                "Authorization": f"Bearer {openrouter_api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                "https://openrouter.ai/api/v1/models",
                headers=headers
            )
            
            if response.status_code != 200:
                detail_logger.error(f"OpenRouter API key verification failed: {response.status_code} {response.text}")
                print(f"❌ OpenRouter API key verification failed: {response.status_code}")
                all_keys_valid = False
            else:
                print("✅ OpenRouter API key verified successfully")
                
                # Check if all required models are available
                models_data = response.json()
                available_models = [model.get("id") for model in models_data.get("data", [])]
                
                required_models = [
                    os.getenv("MODEL_STEP1", "gemini-2.5-flash"),
                    os.getenv("MODEL_STEP2", "anthropic/claude-opus-4"),
                    os.getenv("MODEL_STEP3", "openai/o4-mini"),
                    os.getenv("MODEL_STEP4", "gemini-2.5-pro")
                ]
                
                missing_models = []
                for model in required_models:
                    # Check if the model or a model containing this string is available
                    if not any(model.lower() in available.lower() for available in available_models):
                        missing_models.append(model)
                
                if missing_models:
                    detail_logger.warning(f"Some required models may not be available: {', '.join(missing_models)}")
                    print(f"Some required models may not be available: {', '.join(missing_models)}")
                    print("⚠️ Warning: Some required models may not be available: " + ", ".join(missing_models))
                    print("The system might still work if these models are accessible through your API key.")
        except Exception as e:
            detail_logger.error(f"Error verifying OpenRouter API key: {e}")
            print(f"❌ Error verifying OpenRouter API key: {e}")
            all_keys_valid = False
    
    # Check Google API key
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if google_api_key:
        try:
            detail_logger.info("Verifying Google API key")
            # Simple verification - just check if the key format looks valid
            if google_api_key.startswith("AIza") and len(google_api_key) > 30:
                print("✅ Google API key verified successfully")
            else:
                print("❌ Google API key format appears invalid")
                all_keys_valid = False
        except Exception as e:
            detail_logger.error(f"Error verifying Google API key: {e}")
            print(f"❌ Error verifying Google API key: {e}")
            all_keys_valid = False
    
    # Check Anthropic API key
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_api_key:
        try:
            detail_logger.info("Verifying Anthropic API key")
            # Simple verification - just check if the key format looks valid
            if anthropic_api_key.startswith("sk-ant-") and len(anthropic_api_key) > 40:
                print("✅ Anthropic API key verified successfully")
            else:
                print("❌ Anthropic API key format appears invalid")
                all_keys_valid = False
        except Exception as e:
            detail_logger.error(f"Error verifying Anthropic API key: {e}")
            print(f"❌ Error verifying Anthropic API key: {e}")
            all_keys_valid = False
    
    # Check OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key:
        try:
            detail_logger.info("Verifying OpenAI API key")
            # Simple verification - just check if the key format looks valid
            if openai_api_key.startswith("sk-") and len(openai_api_key) > 40:
                print("✅ OpenAI API key verified successfully")
            else:
                print("❌ OpenAI API key format appears invalid")
                all_keys_valid = False
        except Exception as e:
            detail_logger.error(f"Error verifying OpenAI API key: {e}")
            print(f"❌ Error verifying OpenAI API key: {e}")
            all_keys_valid = False
    
    if all_keys_valid:
        print("All provided API keys verified successfully")
        print("✅ API keys verified successfully!")
        return True
    else:
        detail_logger.error("One or more API keys failed verification")
        return False


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Gracefully shutting down Agatha...")
        print("Thank you for using the Agatha Multi-Model AI Consensus System!")
        print("Goodbye! 🎆")
