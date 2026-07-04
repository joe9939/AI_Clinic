# AI Clinic - Model Adapters
# Abstracts the patient (target model) and doctor (judge model) behind a common interface

import httpx


class PatientModel:
    """The model being examined. Could be any API-compatible LLM."""

    def __init__(self, api_key: str, model: str, base_url: str = "https://api.deepseek.com/v1"):
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")

    @property
    def name(self) -> str:
        return self._model

    async def chat(self, prompt: str) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self._model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0
                },
                timeout=120
            )
            return resp.json()["choices"][0]["message"]["content"]


class DoctorModel:
    """The judge model that diagnoses the patient."""

    def __init__(self, api_key: str, model: str = "deepseek-chat",
                 base_url: str = "https://api.deepseek.com/v1"):
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")

    async def chat(self, prompt: str) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self._model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2
                },
                timeout=120
            )
            return resp.json()["choices"][0]["message"]["content"]
