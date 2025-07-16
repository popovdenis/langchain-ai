from dependencies.container import container
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
import logging
import os

from services.metrics_analyzer import MetricsAnalyser
from utils.logger import setup_logger
from utils.sql import clean_sql

class BaseAgent:
    def __init__(self):
        self.llm = container.llm
        self.db = container.sql_db
        self.mycursor = container.mysql_connection.cursor()
        self.metric_weights = {
            "homework_submitted": float(os.getenv("WEIGHT_HOMEWORK_SUBMITTED", 0.1)),
            "homework_on_time": float(os.getenv("WEIGHT_HOMEWORK_ON_TIME", 0.1)),
            "homework_score": float(os.getenv("WEIGHT_HOMEWORK_SCORE", 0.2)),
            "attendance": float(os.getenv("WEIGHT_ATTENDANCE", 0.2)),
            "student_participation": float(os.getenv("WEIGHT_STUDENT_PARTICIPATION", 0.1)),
            "teacher_participation": float(os.getenv("WEIGHT_TEACHER_PARTICIPATION", 0.1)),
            "test_score": float(os.getenv("WEIGHT_TEST_SCORE", 0.1)),
        }
        self.analyser = MetricsAnalyser(llm=self.llm, metric_weights=self.metric_weights)
        self.logger = setup_logger(self.__class__.__name__)

    def _get_schema(self, _: dict = None):
        return self.db.get_table_info()

    def _run_llm_sql_chain(self, question: str, stop: str = None) -> str:
        prompt = ChatPromptTemplate.from_template("""
            Use schema to answer question. Return valid SQL only.
            Schema:
            {schema}

            Question:
            {question}
            SQL Query:
        """)
        llm = self.llm
        if stop:
            llm = llm.bind(stop=stop)

        try:
            chain = (
                RunnablePassthrough.assign(schema=self._get_schema)
                | prompt
                | llm
                | StrOutputParser()
            )

            response = chain.invoke({"question": question})

            # Normalize to string safely
            if hasattr(response, "content"):
                raw_sql = response.content
            else:
                raw_sql = str(response)

            # Clean and log
            sql = clean_sql(raw_sql.strip())
            logging.info(f"Generated SQL:\n{sql}")

            return sql
        except Exception as e:
            logging.error(f"Error: {e}")
            raise

    def _analyse_metrics(self, parsed_result: list[float]) -> list[dict]:
        return self.analyser.analyse(parsed_result)