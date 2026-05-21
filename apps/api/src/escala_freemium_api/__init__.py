"""MudAção Escala — API freemium.

Camada fina sobre o engine `escala-engine`. Expõe:
- POST /simulate    → roda simulate() pra 1 loja
- POST /extrapolate → projeta 1 loja → N lojas
- POST /lead        → grava lead no Supabase + dispara email Resend
- GET  /health      → 200 OK
- GET  /version     → versão do app + engine
"""

__version__ = "0.1.0"
