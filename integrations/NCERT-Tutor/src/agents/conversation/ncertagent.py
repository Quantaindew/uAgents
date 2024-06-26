# Here we demonstrate how we can create a question reading system agent that is compatible with DeltaV

# After running this agent, it can be registered to DeltaV on Agentverse Services tab. For registration you will have to use the agent's address

# Import required libraries
import requests
from uagents import Model, Protocol, Agent, Context
from ai_engine import UAgentResponse, UAgentResponseType
import json
from summarizer import send_pdf_content
from ncert_data import ncert_data
from uagents.setup import fund_agent_if_low

AGENT_MAILBOX_KEY = "99a95410-3607-41fe-8d42-c14c8b356b11"

agent = Agent(
    name="Question System",
    seed="your_agenasdasdasdastdsfdsf_seed_here",
    port=8000,
    endpoint="http://localhost:8020/submit",
    mailbox=f"{AGENT_MAILBOX_KEY}@https://agentverse.ai",
)


# Define Question Reading Model
class Question(Model):
    question: str
    chapter: int
    subject: str
    standard: int


class Inputmod(Model):
    question: str
    chapter: str
    subject: str
    standard: int


class End(Model):
    msg: str


# Define Protocol for question reading system
question_protocol = Protocol("Question System")

fund_agent_if_low(agent.wallet.address())

json_file_path = "../utils/ncert.json"


def levenshtein_distance(s1, s2):
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def find_chapter_number(chapter_name):  # Define the correct path to your JSON file

    data = ncert_data

    min_distance = float("inf")
    closest_match = None

    # Iterate through each object in the list
    for item in data:
        # Search for the chapter by name within the current standard's chapters
        for chapter in item["chapters"]:
            distance = levenshtein_distance(
                chapter["name"].lower(), chapter_name.lower()
            )
            if distance < min_distance:
                min_distance = distance
                closest_match = chapter

    # If a closest match was found with a reasonable distance, return its number
    if closest_match and min_distance <= 3:  # Assuming a typo tolerance of 3 characters
        return closest_match["number"]
    else:
        return f"Chapter '{chapter_name}' not found or too many typos."


@agent.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info("Question System Agent Started")
    ctx.logger.info(f"{agent.address}")

    ##Local Testing code snippet, uncomment the code below to run locally
    ##intentionally added typo to test levenshtien distance algorithm
    chapter_name = "alice in wonland"
    chapter_num = find_chapter_number(chapter_name)
    standard = 4
    ctx.logger.info(
        f"Chapter Name : {chapter_name}, Chapter number: {chapter_num}, standard: {standard}"
    )
    message = await send_pdf_content(
        ctx,
        agent.address,
        Question(
            question=f"Can you provide a summary of the chapter {chapter_name} from standard {standard} English?",
            chapter=chapter_num,
            subject="english",
            standard=standard,
        ),
    )


# Define a handler for the Question system protocol
@question_protocol.on_message(model=Inputmod, replies=UAgentResponse)
async def on_question_request(ctx: Context, sender: str, msg: Inputmod):
    # Printing the question response on logger
    if msg.question:
        question = msg.question
    else:
        question = "Can you provide a summary of the chapter"
    chapter = find_chapter_number(msg.chapter)
    ctx.logger.info(f"Received question request from {sender}")
    ctx.logger.info(
        f"Question: {question}, Chapter: {chapter}, Subject: {msg.subject}, Standard: {msg.standard}"
    )
    message = await send_pdf_content(
        ctx,
        sender,
        Question(
            question=msg.question,
            chapter=chapter,
            subject=msg.subject,
            standard=msg.standard,
        ),
    )
    # Creating hyperlink and sending final response to the DeltaV GUI
    ctx.logger.info(f"Final Message: {message}")
    await ctx.send(
        sender, UAgentResponse(message=message, type=UAgentResponseType.FINAL)
    )


# Include the Generate Question protocol in your agent
agent.include(question_protocol)


if __name__ == "__main__":
    agent.run()
