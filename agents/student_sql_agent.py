from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from config.settings import Settings


class StudentSQLAgent:
    def __init__(self, model_name="gpt-4", temperature=0.0, current_week=None):
        self.db = SQLDatabase.from_uri(Settings.postgres_uri())
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            openai_api_key=Settings.OPENAI_API_KEY
        )
        self.current_week = current_week

        self.prompt = PromptTemplate.from_template(
            """
            Assume current week is {week_now}.
            Given an input question, create a syntactically correct PostgreSQL query to run.
            Use the following table:
            student_metrics(student_id, week, attendance, homework_submitted, homework_on_time, homework_score, test_score, student_talk_percent, teacher_talk_percent, silence_percent)

            Question: {question}
            SQLQuery:
            """
        )

    def run_query(self, natural_language_prompt: str) -> str:
        chain: Runnable = self.prompt | self.llm

        sql_query = chain.invoke({
            "question": natural_language_prompt,
            "week_now": self.current_week
        }).content

        print("\nRaw prompt to GPT:")
        print(self.prompt.format(
            question=natural_language_prompt,
            week_now=self.current_week
        ))

        print("\nGPT Response:")
        print(sql_query)

        try:
            result = self.db.run(sql_query)
        except Exception as e:
            return f"Error while running SQL: {e}\nGenerated SQL:\n{sql_query}"

        return f"Generated SQL:\n{sql_query}\n\nResult:\n{result}"