import os
import time
import json
from google import genai
from google.genai import types
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

class ModelLLM:

    def __init__(self, device_map="auto"):
        self.PATH_self_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

        self.device_map = device_map
        
        config = self.load_config()
        self.local_model = config.get("LocalMode", True)
        self.api_key = config.get("API_KEY", None)

        self.load_LLM()


    def load_config(self):

        config_path = os.path.join(self.PATH_self_dir, 'data', 'model_config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            config = {"LocalMode": True, "API_KEY": None}
        return config


    def load_LLM(self):
        self.ARGS_generation = {"max_new_tokens": 512, "temperature": 0.2, "do_sample": True}
        if self.local_model:
            self.ModelLoaded = "microsoft/Phi-3.5-mini-instruct"
            self.tokenizer = AutoTokenizer.from_pretrained(self.ModelLoaded, trust_remote_code=False, padding_side='left')
            self.model = AutoModelForCausalLM.from_pretrained(self.ModelLoaded, device_map=self.device_map, torch_dtype="auto", trust_remote_code=False)
            print(f"\t\t [✅-INFO] Model {self.ModelLoaded} loaded successfully. Default Generation Args: {self.ARGS_generation}")

        else:
            if not self.api_key:
                raise ValueError("API_KEY for Gemini is not set in model_config.json!")
            os.environ['GEMINI_API_KEY'] = self.api_key
            self.gemini_client = genai.Client()
            self.gemini_model = "gemini-2.5-flash"
            self.gemini_types = types
            self.ModelLoaded = self.gemini_model
            print(f"\t\t [✅-INFO] Model {self.ModelLoaded} loaded successfully. Default Generation Args: {self.ARGS_generation}")


    def query(self, prompt, generation_args:dict=None, thinking_budget=False):
        """Query the model with a prompt and return the response. For Gemini, thinking_budget can be set (default True)."""

        if generation_args is None:
                generation_args = self.ARGS_generation
        t1 = time.time()

        if self.local_model:
            print(f"\t\t [🧠-INFO] Query with Model - {self.ModelLoaded} - GenerationArgs - {generation_args}")
            response = self.infer_local_llm(prompt, generation_args)
        
        else:
            generation_args.update({"thinking_budget":thinking_budget})
            print(f"\t\t [🧠-INFO] Query with Model - {self.ModelLoaded} - GenerationArgs - {generation_args}")
            response = self.infer_gemini_llm(prompt, generation_args, thinking_budget)
            
        print("\t\t [🧠-INFO] Total Generation Time:", time.time() - t1)
        return response


    def infer_local_llm(self, prompt, generation_args):
        inputs = self.tokenizer.apply_chat_template(prompt, add_generation_prompt=True, return_tensors="pt", padding=True).to(self.model.device)
        with torch.no_grad():
            output = self.model.generate(inputs, **generation_args)
        tokenized_response = self.tokenizer.batch_decode(output, skip_special_tokens=False, clean_up_tokenization_spaces=True)

        if len(tokenized_response) > 1:
            response = []
            for tok_res in tokenized_response:
                response.append(tok_res.split("<|assistant|>")[-1].split("<|end|>")[0].strip())
        else:
            response = tokenized_response[0].split("<|assistant|>")[-1].split("<|end|>")[0].strip()
        return response


    def infer_gemini_llm(self, prompt, generation_args, thinking_budget):

        if (isinstance(prompt[0], list)):
            
            response = []
            for indv_prompt in prompt:

                if thinking_budget:
                    config = self.gemini_types.GenerateContentConfig(system_instruction=indv_prompt[0]['content'])
                else:
                    config = self.gemini_types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_budget=0),
                                                                        system_instruction=indv_prompt[0]['content'])
                content = indv_prompt[1]['content']
                gemni_response = self.gemini_client.models.generate_content(
                        model=self.gemini_model,
                        contents=content,
                        config=config)
                response.append(gemni_response.text)
        else:

            if thinking_budget:
                config = self.gemini_types.GenerateContentConfig(system_instruction=prompt[0]['content'])
            else:
                config = self.gemini_types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_budget=0),
                                                                    system_instruction=prompt[0]['content'])
            content = prompt[1]['content']
            gemni_response = self.gemini_client.models.generate_content(
                    model=self.gemini_model,
                    contents=content,
                    config=config)
            response = gemni_response.text

        return response