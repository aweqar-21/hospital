"""统一模型加载接口 —— 支持 transformers / llama.cpp 等多种后端。"""
from enum import Enum
from typing import Any, Optional


class Backend(str, Enum):
    TRANSFORMERS = "transformers"
    LLAMA_CPP = "llama_cpp"
    OLLAMA = "ollama"


class ModelLoader:
    """加载不同后端的本地模型。"""

    def __init__(self, backend: Backend = Backend.TRANSFORMERS) -> None:
        self.backend = backend
        self._model: Any = None
        self._tokenizer: Any = None

    def load(
        self,
        model_name_or_path: str,
        *,
        device: str = "cpu",
        quantize: Optional[str] = None,
        **kwargs,
    ) -> None:
        """加载模型和分词器。"""
        if self.backend == Backend.TRANSFORMERS:
            self._load_transformers(model_name_or_path, device, quantize, **kwargs)
        elif self.backend == Backend.LLAMA_CPP:
            self._load_llama_cpp(model_name_or_path, **kwargs)
        elif self.backend == Backend.OLLAMA:
            self._model = model_name_or_path  # Ollama 只需模型名
        else:
            raise ValueError(f"不支持的后端: {self.backend}")

    def _load_transformers(
        self, path: str, device: str, quantize: Optional[str], **kwargs
    ) -> None:
        """使用 HuggingFace Transformers 加载。"""
        from transformers import AutoModelForCausalLM, AutoTokenizer

        model_kwargs = {}
        if quantize == "4bit":
            model_kwargs["load_in_4bit"] = True
        elif quantize == "8bit":
            model_kwargs["load_in_8bit"] = True

        self._tokenizer = AutoTokenizer.from_pretrained(path, trust_remote_code=True)
        self._model = AutoModelForCausalLM.from_pretrained(
            path,
            device_map=device if device != "cpu" else None,
            trust_remote_code=True,
            **model_kwargs,
            **kwargs,
        )

    def _load_llama_cpp(self, path: str, **kwargs) -> None:
        """使用 llama.cpp 加载 GGUF 模型。"""
        from llama_cpp import Llama

        self._model = Llama(
            model_path=path,
            n_ctx=kwargs.get("n_ctx", 2048),
            n_threads=kwargs.get("n_threads", 4),
            verbose=False,
        )

    @property
    def is_loaded(self) -> bool:
        return self._model is not None
