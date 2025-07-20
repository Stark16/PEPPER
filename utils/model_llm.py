import os
import time
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

class ModelLLM:

    def __init__(self, local_model = True, device_map="auto"):
        self.PATH_self_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        self.local_model = local_model
        self.device_map = device_map

        if local_model:
            self.ModelLoaded = "microsoft/Phi-3.5-mini-instruct"
            self.ARGS_generation = {"max_new_tokens": 512, "temperature": 0.2, "do_sample": True}
            self.load_LLM()


    def load_LLM(self):
        if self.local_model:
            self.tokenizer = AutoTokenizer.from_pretrained(self.ModelLoaded, trust_remote_code=False, padding_side='left')
            self.model = AutoModelForCausalLM.from_pretrained(self.ModelLoaded, device_map=self.device_map, torch_dtype="auto", trust_remote_code=False)
            print(f"\t\t [✅-INFO] Model {self.ModelLoaded} loaded successfully. Default Generation Args: {self.ARGS_generation}")


    def query(self, prompt, generation_args=None):
        """Query the model with a prompt and return the response."""

        if self.local_model:
            if generation_args is None:
                generation_args = self.ARGS_generation

            print(f"\t\t [🧠-INFO] Query with Model - {self.ModelLoaded} - GenerationArgs - {generation_args}")
            inputs = self.tokenizer.apply_chat_template(prompt, add_generation_prompt=True, return_tensors="pt", padding=True).to(self.model.device)

            t1 = time.time()
            with torch.no_grad():
                output = self.model.generate(inputs, **generation_args)
            print("\t\t [🧠-INFO] Total Generation Time:", time.time() - t1)

            tokenized_response = self.tokenizer.batch_decode(output, skip_special_tokens=False, clean_up_tokenization_spaces=True)

            if len(tokenized_response) > 1:
                response = []
                for tok_res in tokenized_response:
                    response.append(tok_res.split("<|assistant|>")[-1].split("<|end|>")[0].strip())
            else:
                response = tokenized_response[0].split("<|assistant|>")[-1].split("<|end|>")[0].strip()
            
            return response
