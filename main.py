from groq import Groq
import os, datetime

client = Groq(
  api_key=os.environ.get('GROQ_API_KEY'),
)

with open("resume.txt", "r") as resume_file:
  resume = resume_file.read()
  
with open("job_description.txt", "r") as job_description_file:
  jobDescrption = job_description_file.read()

completion = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
      {
        "role": "user",
        "content": "Build a custom resume for this job posting here is the resume: "+ resume+ " and here is the job description: "+ jobDescrption
        },
      {
        
        "role": "assistant",
        "content": "Please provide the job posting details, and I'll create a resume tailored to the job description."
        }],
    temperature=1,
    max_completion_tokens=1024,
    top_p=1,
    stream=True,
    stop=None,
)

for chunk in completion:
    print(chunk.choices[0].delta.content or "", end="")
    
timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
output_file = "resume-"+timestamp+".txt"
with open(output_file, "w") as output:
    output.write(completion.choices[0].message.content)
