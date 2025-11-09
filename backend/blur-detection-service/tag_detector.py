import os
import base64
from openai import OpenAI
from typing import List

class AITagger:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def generate_tags(self, image_bytes: bytes) -> List[str]:
        base64_image = base64.b64encode(image_bytes).decode('utf-8')

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Please describe the main objects or places shown in this image using only 1 english word. Example: Dog, Park, Flower"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=50
        )

        tag = response.choices[0].message.content
        return tag

ai_tagger = AITagger()
