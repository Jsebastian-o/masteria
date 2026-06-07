#!/bin/bash
set -a
source .env
set +a

uvicorn app.main:app --reload
