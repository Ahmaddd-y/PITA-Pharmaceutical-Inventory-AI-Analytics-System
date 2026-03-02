# ai.py
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
import os
from dotenv import load_dotenv
import pandas as pd

load_dotenv()
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

class TrendAnalysisFacade:
    """
    FACADE PATTERN:
    Hides the complexity of initializing LLMs, managing API keys, 
    and engineering prompts behind a simple interface.
    """
    def __init__(self, model_type="cloud"):
        self.model_type = model_type
        self._llm = self._initialize_llm()

    def _initialize_llm(self):
        """Internal method to handle the complex setup of the LLM."""
        if self.model_type == "cloud":
            # You can handle missing keys gracefully here if needed
            return ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=GEMINI_KEY)
        elif self.model_type == "local":
            return ChatOllama(model="qwen2.5:3b")
        else:
            raise ValueError("Unknown model type")

    def get_prediction(self, transaction_df, inventory_df):
        """
        The simplified interface for the client.
        """
        
        sales = transaction_df[transaction_df['type'] == 'Sale']
        if sales.empty:
            return "No sales data available for analysis."
            
        top_sellers = sales['drug'].value_counts().head(5).to_dict()
        low_stock = inventory_df[inventory_df['quantity'] <= inventory_df['reorder_level']]['drug'].tolist()
        
        prompt = (
            f"Analyze this pharmaceutical data:\n"
            f"Top selling drugs: {top_sellers}\n"
            f"Drugs currently low in stock: {low_stock}\n\n"
            "Provide a brief executive summary. Suggest restocking priorities and identify any sales trends."
        )
        
        # 3. Invoke the Subsystem
        try:
            response = self._llm.invoke(prompt)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            return f"Error connecting to AI service: {str(e)}"

def analyze_trends(transaction_df, inventory_df, model_type="cloud"):
    facade = TrendAnalysisFacade(model_type)
    return facade.get_prediction(transaction_df, inventory_df)