# Sample Queries and Outputs for Highwatch AI RAG System

Here are examples of how the system handles different types of questions, from simple data retrieval to complex document summarization.

---

### 1. Simple Data Retrieval
**Query:**
> "What was Amazon's operating cash flow for 2024?"

**AI Output:**
> Amazon's operating cash flow was $115.9 billion for the trailing twelve months in 2024.
> 
> **Sources:**
> - `AMZN-Q4-2025-Earnings-Release.pdf`

---

### 2. Complex Analysis & Comparison
**Query:**
> "Compare the Free Cash Flow between 2024 and 2025 based on the earnings release."

**AI Output:**
> Based on the earnings release, Amazon's Free Cash Flow actually declined year-over-year. 
> * For the trailing twelve months in **2024**, Free Cash Flow was **$14.8 billion**.
> * For the trailing twelve months in **2025**, Free Cash Flow dropped to **$11.2 billion**.
> 
> This decline occurred despite strong revenue growth, primarily due to significantly increased capital expenditures, which rose from $82.9 billion in 2024 to $131.8 billion in 2025.
> 
> **Sources:**
> - `AMZN-Q4-2025-Earnings-Release.pdf`

---

### 3. Document Summarization
**Query:**
> "Please provide a comprehensive summary of the document: AMZN-Q4-2025-Earnings-Release.pdf"

**AI Output:**
> Here is a comprehensive summary of Amazon's Q4 2025 Earnings Release:
> 
> **Cash Flow and Balance Sheet:**
> * **Operating Cash Flow:** Increased to $139.5 billion for the trailing twelve months, up from $115.9 billion in 2024.
> * **Free Cash Flow:** Decreased to $11.2 billion for the trailing twelve months, down from $14.8 billion in 2024.
> * **Capital Expenditures:** Increased significantly to $131.8 billion for the trailing twelve months, compared with $82.9 billion in 2024.
> 
> **Key Metrics:**
> * **Operating Margin:** Improved to 11.2% for the trailing twelve months, up from 10.8% in 2024.
> * **Return on Equity (ROE):** Rose to 23.1% for the trailing twelve months, compared with 20.5% in 2024.
> 
> **Guidance and Outlook:**
> The company did not provide specific financial guidance for the first quarter of 2026, but noted that it expects to continue to invest heavily in its businesses and expand its offerings.
> 
> **Conclusion:**
> Overall, Amazon's fourth-quarter 2025 earnings release showed strong revenue growth and improving profitability, driven by the company's continued expansion into new markets and its investments in its businesses. However, the company's free cash flow declined due to increased capital expenditures.
> 
> **Sources:**
> - `AMZN-Q4-2025-Earnings-Release.pdf`

---

### 4. Out of Scope / Missing Information (Hallucination Prevention)
**Query:**
> "What is the company's policy on remote work?"

**AI Output:**
> I couldn't find any relevant information about remote work policies in your currently synced Google Drive documents. If you have an employee handbook or policy document, please ensure it is uploaded to your Drive and synced so I can analyze it for you!
> 
> **Sources:**
> *(None)*

---

### 5. Conversational Follow-up (Context Awareness)
**Query 1:**
> "What was the operating margin in 2025?"

**AI Output 1:**
> The operating margin for the trailing twelve months in 2025 was 11.2%.

**Query 2 (Follow-up):**
> "How does that compare to the previous year?"

**AI Output 2:**
> That represents an improvement! The operating margin for the trailing twelve months in 2024 was 10.8%, meaning it increased by 0.4% in 2025.
> 
> **Sources:**
> - `AMZN-Q4-2025-Earnings-Release.pdf`