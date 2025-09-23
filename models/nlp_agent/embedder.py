import torch
from transformers import AutoTokenizer, AutoModel
from typing import Dict, Any
from mecab import MeCab

class TextEmbedder:
    def __init__(self, model_name: str = "jhgan/ko-sroberta-multitask"):
        print(f"임베딩 모델 로딩 중: {model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.mecab = MeCab()
        
        self.device = torch.device('cpu')
        self.model.to(self.device)
        self.model.eval()
        print("임베딩 모델 로딩 완료.")

    def _mean_pooling(self, model_output, attention_mask):
        token_embeddings = model_output[0]
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    
    def embed_text(self, text: str) -> Dict[str, any]:
        """
        주어진 텍스트를 임베딩 벡터로 변환합니다.
        
        Args:
            text (str): 임베딩할 텍스트.
        
        Returns:
            Dict[str, any]: 임베딩 벡터를 포함하는 딕셔너리.
        """
        encoded_input = self.tokenizer(text, padding=True, truncation=True, return_tensors='pt').to(self.device)
        
        with torch.no_grad():
            model_output = self.model(**encoded_input)
        
        sentence_embeddings = self._mean_pooling(model_output, encoded_input['attention_mask'])
        
        sentence_embeddings = torch.nn.functional.normalize(sentence_embeddings, p=2, dim=1)
        
        return {
            "embedding": sentence_embeddings.cpu()
        }