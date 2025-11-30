# penta-core

A simple HTTP server application.

## Setup

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the server:
   ```bash
   python server.py
   ```

## Configuration

Configure the server using environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| HOST | 0.0.0.0 | Server host address |
| PORT | 8000 | Server port |

## Endpoints

- `GET /health` - Health check endpoint (returns `{"status": "healthy"}`)

## License

MIT License - see [LICENSE](LICENSE) for details.