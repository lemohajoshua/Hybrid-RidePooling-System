\# 🚗 Hybrid Ride-Pooling and Delivery Optimisation System



A simulation-based hybrid ride-pooling and last-mile delivery optimisation system for Owerri's urban-rural transport network.



\## Features

\- 🧑‍🤝‍🧑 Ride-Pooling (match 2 passengers going to same destination)

\- 📦 Delivery Task Allocation (rural deliveries to reduce deadhead trips)

\- 🗺️ Interactive Map (Leaflet.js)

\- 📊 Simulation Dashboard (real-time metrics)

\- 🔐 Authentication (Passenger/Driver/Admin roles)



\## Tech Stack

\- \*\*Frontend:\*\* HTML, CSS, JavaScript, Leaflet.js

\- \*\*Backend:\*\* Python, FastAPI, Supabase (PostgreSQL)

\- \*\*Algorithms:\*\* Insertion Heuristic, Deadhead Reduction Scoring, Hybrid Mode Switching



\## Setup

1\. Clone the repo

2\. Install backend dependencies: `pip install -r backend/requirements.txt`

3\. Create `.env` file with Supabase credentials

4\. Run backend: `python -m app.main`

5\. Open frontend: `http://localhost:5500/pages/landing/index.html`



\## Author

lemohajoshua



\## License

MIT

uvicorn app.main:app --reload --port 8000