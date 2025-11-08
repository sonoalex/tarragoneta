from app import create_app
from app.cli import init_db_command, create_sample_data
import click

app = create_app()

# Register CLI commands
@app.cli.command('init-db')
def init_db():
    """Initialize the database using Flask-Migrate."""
    init_db_command()

@app.cli.command('create-sample-data')
def create_sample():
    """Create sample data for testing."""
    create_sample_data()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=app.config['DEBUG'])
