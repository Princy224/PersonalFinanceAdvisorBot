# Personal Finance Advisor Bot

An AI-powered Personal Finance Advisor Bot designed to help users manage their income, expenses, budgets, and financial activities.

## Project Overview
The Personal Finance Advisor Bot helps users track financial transactions and understand their spending habits. It provides financial insights and budgeting assistance through an interactive web application.

## Features
- Income and expense tracking
- Personal budget management
- Transaction management
- Financial insights and suggestions
- AI-powered financial assistance using Gemini API
- Local demo fallback when the AI service is unavailable
- Database management using SQLite

## Technology Stack
- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Python, Flask
- **Database:** SQLite
- **AI Integration:** Google Gemini API
- **Version Control:** Git and GitHub

## Installation and Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/Princy224/PersonalFinanceAdvisorBot.git
   ```

2. Navigate to the project directory:

   ```bash
   cd PersonalFinanceAdvisorBot
   ```

3. Create a virtual environment:

   ```bash
   python -m venv venv
   ```

4. Activate the environment on Windows:

   ```powershell
   venv\Scripts\Activate.ps1
   ```

5. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

6. Configure your environment variables in `.env` if required.

7. Run the application:

   ```bash
   python app.py
   ```

8. Open your browser:

   ```text
   http://127.0.0.1:5000
   ```

## Project Structure

```text
PersonalFinanceAdvisorBot/
│
├── app.py
├── finance.db
├── requirements.txt
├── .env
├── .gitignore
├── templates/
└── static/
```

## Developer
**Princy Bhardwaj**

GitHub: https://github.com/Princy224

## Note
This project is developed for educational purposes and provides general financial guidance, not professional financial advice.

