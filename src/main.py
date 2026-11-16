import os
import json
import gc
import secrets
import httpx

from typing import Literal, Optional
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel, Field
from fastapi.concurrency import run_in_threadpool
from fastembed import TextEmbedding


# CONFIGURATION

EMBEDDING_MODEL = (
    "sentence-transformers/"
    "paraphrase-multilingual-MiniLM-L12-v2"
)

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434/api/generate"
)
OLLAMA_MODEL = "qwen2.5:1.5b"

app = FastAPI(
    title="MATAHATI AI Service",
    description="AI Batik Recommendation Service",
    version="0.2.0"
)

# AUTHENTICATION

def verify_internal_key(
    x_internal_key: Optional[str] = Header(default=None)
):
    expected_key = os.getenv("AI_SERVICE_KEY")

    if not expected_key:
        raise HTTPException(
            status_code=503,
            detail="AI_SERVICE_KEY belum dikonfigurasi."
        )

    if not x_internal_key or not secrets.compare_digest(
        x_internal_key, expected_key
    ):
        raise HTTPException(
            status_code=401,
            detail="Internal key tidak valid."
        )


# REQUEST SCHEMAS

class EmbedRequest(BaseModel):
    type: Literal["query", "document"]
    inputs: list[str] = Field(min_length=1, max_length=32)


class Preferences(BaseModel):
    colors: list[str] = Field(default_factory=list)

    motifType: Optional[
        Literal["classic", "semi_modern"]
    ] = None

    occasions: list[str] = Field(default_factory=list)

    targetUser: Optional[
        Literal["men", "women", "unisex"]
    ] = None

    maxPriceIdr: Optional[int] = None
    notes: Optional[str] = None


class Motif(BaseModel):
    slug: str
    name: str
    type: Literal["classic", "semi_modern"]
    philosophy: Optional[str] = None


class Candidate(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    material: Optional[str] = None
    philosophy: Optional[str] = None
    category: str
    colors: list[str] = Field(default_factory=list)
    occasions: list[str] = Field(default_factory=list)

    targetUser: Literal["men", "women", "unisex"]

    priceIdr: int

    availability: Literal[
        "available",
        "made_to_order",
        "sold_out"
    ]

    motif: Optional[Motif] = None


class RecommendRequest(BaseModel):
    locale: Literal[
        "id", "ms", "en", "th", "fil",
        "zh", "ta", "vi", "lo", "my",
        "km", "tet", "pt"
    ] = "id"

    preferences: Preferences

    limit: int = Field(default=5, ge=1, le=10)

    candidates: list[Candidate] = Field(
        min_length=1,
        max_length=50
    )


# EMBEDDING

def generate_embeddings(inputs: list[str]):
    model = None

    try:
        model = TextEmbedding(
            model_name=EMBEDDING_MODEL
        )

        embeddings = list(model.embed(inputs))

        return [
            embedding.tolist()
            for embedding in embeddings
        ]

    finally:
        if model is not None:
            del model

        gc.collect()


# LANGUAGE INSTRUCTION

def get_language(locale: str):
    languages = {
        "id": "Bahasa Indonesia",
        "ms": "Bahasa Melayu",
        "en": "English",
        "th": "Thai",
        "fil": "Filipino",
        "zh": "Chinese",
        "ta": "Tamil",
        "vi": "Vietnamese",
        "lo": "Lao",
        "my": "Burmese",
        "km": "Khmer",
        "tet": "Tetum",
        "pt": "Portuguese"
    }

    return languages.get(locale, "Bahasa Indonesia")


# API ENDPOINTS

@app.get("/")
def home():
    return {
        "message": "MATAHATI AI Service is running"
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "embeddingModel": EMBEDDING_MODEL
    }


# EMBED ENDPOINT

@app.post("/embed")
async def embed(
    request: EmbedRequest,
    _: None = Depends(verify_internal_key)
):
    try:
        embeddings = await run_in_threadpool(
            generate_embeddings,
            request.inputs
        )

        return {
            "model": EMBEDDING_MODEL,
            "embeddings": embeddings
        }

    except Exception as exc:
        print(f"ERROR EMBEDDING: {exc}")

        raise HTTPException(
            status_code=500,
            detail="Gagal menghasilkan embedding."
        )



# RECOMMEND ENDPOINT

@app.post("/recommend")
async def recommend(
    request: RecommendRequest,
    _: None = Depends(verify_internal_key)
):
    preferences = request.preferences.model_dump()

    candidates = [
        candidate.model_dump()
        for candidate in request.candidates
        if candidate.availability != "sold_out"
    ]

    if not candidates:
        return {"items": []}

    language = get_language(request.locale)

    prompt = f"""
Kamu adalah AI Assistant rekomendasi produk batik MATAHATI.

Tugasmu adalah mengurutkan kandidat produk berdasarkan
kecocokan dengan preferensi pengguna dan memberikan
alasan rekomendasi yang informatif.

PREFERENSI PENGGUNA:
{json.dumps(preferences, ensure_ascii=False)}

KANDIDAT PRODUK:
{json.dumps(candidates, ensure_ascii=False)}

ATURAN:
1. Pilih hanya produk dari daftar kandidat.
2. Jangan membuat ID atau produk baru.
3. Jangan mengarang informasi produk.
4. Pertimbangkan warna, jenis motif, acara,
   dan catatan pengguna.
5. Budget, target pengguna, dan stok sudah difilter BE.
6. Jangan merekomendasikan produk sold_out.
7. Gunakan informasi filosofi hanya jika tersedia.
8. Jangan mengarang filosofi motif.
9. Urutkan produk dari yang paling sesuai.
10. Berikan alasan yang spesifik berdasarkan data produk.
11. Gunakan bahasa {language}.
12. Setiap alasan maksimal 500 karakter.
13. Maksimal {request.limit} produk.
14. Jika tidak ada kandidat yang cocok, kembalikan
    daftar items kosong.
15. Warna yang tidak sesuai preferensi pengguna
    tidak boleh dianggap cocok.
16. Acara produk harus sesuai dengan acara yang
    dipilih pengguna jika preferensi acara tersedia.
17. Jangan memaksakan rekomendasi hanya untuk
    memenuhi jumlah limit.
18. Jika kandidat tidak memenuhi preferensi utama,
    jangan masukkan kandidat tersebut.


FORMAT OUTPUT JSON:
{{
    "items": [
        {{
            "productId": "ID_PRODUK",
            "reason": "Alasan rekomendasi"
        }}
    ]
}}

Jangan tambahkan teks di luar JSON.
"""

    try:
        async with httpx.AsyncClient(
            timeout=120.0
        ) as client:

            response = await client.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "keep_alive": "5m",
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 1024,
                        "num_ctx": 4096
                    }
                }
            )

            response.raise_for_status()

            raw_result = response.json()["response"]

        print("\n===== HASIL MENTAH LLAMA =====")
        print(raw_result)

        generated = json.loads(raw_result)

        valid_ids = {
            candidate["id"]
            for candidate in candidates
        }

        final_items = []
        used_ids = set()

        for item in generated.get("items", []):

            if not isinstance(item, dict):
                continue

            product_id = item.get("productId")
            reason = item.get("reason")

            if product_id not in valid_ids:
                continue

            if product_id in used_ids:
                continue

            if not isinstance(reason, str) or not reason.strip():
                continue

            final_items.append({
                "productId": product_id,
                "reason": reason.strip()[:500]
            })

            used_ids.add(product_id)

            if len(final_items) >= request.limit:
                break

        return {
            "items": final_items
        }

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Proses rekomendasi AI melebihi batas waktu."
        )

    except httpx.HTTPError as exc:
        print(f"ERROR OLLAMA HTTP: {exc}")

        raise HTTPException(
            status_code=502,
            detail="Tidak dapat menghubungi Ollama."
        )

    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"ERROR HASIL LLAMA: {exc}")

        raise HTTPException(
            status_code=502,
            detail="Format hasil rekomendasi AI tidak valid."
        )

    except Exception as exc:
        print(f"ERROR RECOMMENDATION: {exc}")

        raise HTTPException(
            status_code=500,
            detail="Terjadi kesalahan pada AI Service."
        )