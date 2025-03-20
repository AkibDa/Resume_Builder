from groq import Groq
import os

client = Groq(
  api_key=os.environ.get('GROQ_API_KEY'),
)
completion = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
      {
        "role": "user",
        "content": "Build a custom resume for this job posting"
        },
      {
        
        "role": "assistant",
        "content": "Sure, I can help you with that. Can you please provide me with the job posting?"
        }],
    temperature=1,
    max_completion_tokens=1024,
    top_p=1,
    stream=True,
    stop=None,
)

for chunk in completion:
    print(chunk.choices[0].delta.content or "", end="")
