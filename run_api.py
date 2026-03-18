#!/usr/bin/env python3
"""Run the Assessment Engine API server."""
import uvicorn

from assessment_engine.api import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "run_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
