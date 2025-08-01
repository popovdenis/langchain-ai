from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import logging

class MetricsAnalyser:
    def __init__(self, metric_weights: dict, llm):
        self.metric_weights = metric_weights
        self.llm = llm

    def analyse(self, metrics: list[float]):
        metric_order = list(self.metric_weights.keys())
        summary = []
        subtotal = 0.0
        min_metric = None
        min_value = None

        for metric, value in zip(metric_order, metrics):
            weighted = round(value * self.metric_weights[metric], 2)
            summary.append({"label": metric.replace("_", " ").title(), "value": weighted})
            subtotal += weighted
            if min_value is None or value < min_value:
                min_value = value
                min_metric = metric

        total_score = round(subtotal * 100, 2)
        motivation_zone = (
            "Red - High Risk" if total_score <= 45 else
            "Yellow - Moderate Risk" if total_score <= 75 else
            "Green - Low Risk"
        )

        try:
            message_prompt = ChatPromptTemplate.from_template("""
                The student's weakest metric is: {metric}.
                Write a motivational message (15+ tokens) to help improve. Return only the message.
            """)
            message_chain = message_prompt | self.llm | StrOutputParser()
            motivation_message = message_chain.invoke({"metric": min_metric.replace("_", " ")}).strip()
        except Exception as e:
            logging.error(f"Motivational message generation failed: {e}")
            motivation_message = "Motivational message could not be generated."

        return {
            "metrics": summary,
            "metric_zone": motivation_zone,
            "subtotal": round(subtotal, 4),
            "total": f"{total_score}%",
            "motivation_message": motivation_message,
        }