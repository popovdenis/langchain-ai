from langchain_core.prompts import ChatPromptTemplate

def build_sql_prompt(schema: str, question: str) -> str:
    """Return a formatted SQL prompt for LangChain."""
    return ChatPromptTemplate.from_template("""
        Use schema to answer question. Return valid SQL only.
        Schema:
        {schema}

        Question:
        {question}
        SQL Query:
    """).format(schema=schema, question=question)