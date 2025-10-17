## Technology Stack

- **Language**: Python 3.13.1
- **Package Manager**: virtualenv
- **Key Dependencies**:
    - beautifulsoup4, requests (web scraping/HTTP)
    - kubernetes (container orchestration)
    - numpy, pandas (data processing)
    - pytest, coverage, mypy (testing & type checking)
    - jinja2 (templating)
    - streamlit (UI)

## Development Guidelines

### Code Style

1. **Type Hints**: Use type hints for all function signatures
2. **Docstrings**: Include docstrings for all public classes and methods
3. **Naming Conventions**:
    - Classes: PascalCase
    - Functions/Variables: snake_case
    - Constants: UPPER_SNAKE_CASE
4. **Import Organization**: Group imports (stdlib, third-party, local)

### Testing

- Use `pytest` for all tests
- Maintain test coverage with `coverage` package
- Test files should mirror source structure in `tests/`
- Run type checking with `mypy` before committing

### Architecture Principles

1. **Modularity**: Keep components loosely coupled
2. **Worker Pattern**: Use the orchestrator for distributed task execution
3. **Caching Strategy**: Utilize multi-level caching (embeddings, costs, analytics)
4. **Memory Management**: Leverage unified memory and vector storage for context
5. **Service Abstraction**: Search services should implement base interfaces

### Key Components

#### Agent System (`src/agent/`)
- Autonomous agent behavior
- Decision-making logic

#### Workers (`src/workers/`)
- Orchestrator manages worker lifecycle
- Context store for shared state
- Template-based task definitions

#### Memory (`src/memory/`)
- Profile management for user context
- Unified memory interface
- Vector storage for semantic search

#### Services (`src/services/`)
- Search implementations (Google, Perplexity, SerpAPI, Wikipedia)
- Backup and recovery
- Cache warming
- Cost tracking
- Embeddings generation

### Configuration

- Environment variables in `.env` (use `.env.example` as template)
- Settings centralized in `src/config/settings.py`
- Separate configs for development/production

### Data Management

- **Conversations**: Store in `data/conversations/`
- **Profiles**: Store in `data/profiles/`
- **Logs**: Separate logs in `cache/logs/` (app.log, errors.log)
- **Backups**: Automated backups to `backups/`

### Running the Application

- **Main Entry**: `main.py` or `run.py`
- **UI**: Streamlit apps in `ui/` directory
- **CLI**: Available through `src/interface/cli.py`

### Best Practices

1. **Error Handling**: Use proper exception handling and logging
2. **Resource Cleanup**: Ensure proper cleanup of resources (connections, files)
3. **Async Operations**: Use async/await for I/O-bound operations where appropriate
4. **Cost Awareness**: Track API costs via cost_tracker service
5. **Cache First**: Check cache before making external API calls
6. **Metrics**: Record metrics for monitoring and optimization

### Documentation

- Keep `DOCS.md`, `ARCHITECTURE.md`, and `QUICKSTART.md` updated
- Document new features in `docs/` directory
- Update `SYSTEM_MAP_COMPLETE.md` for system changes
- Worker implementation details in `src/workers/IMPLEMENTATION.md`

### Git Workflow

1. Create feature branches from main
2. Write tests for new features
3. Run test suite before committing
4. Keep commits atomic and descriptive
5. Update documentation with code changes

### Security

- Never commit `.env` files
- Use environment variables for sensitive data
- Validate all external inputs
- Sanitize data before storage

### Performance

- Profile code for bottlenecks
- Optimize expensive operations
- Use caching strategically
- Monitor memory usage with large datasets

## Common Tasks

### Adding a New Search Service

1. Create implementation in `src/services/search/`
2. Extend `base.py` interface
3. Register in `__init__.py`
4. Add configuration to settings
5. Write tests
6. Update documentation

### Adding a New Worker Type

1. Define in `src/workers/`
2. Register with orchestrator
3. Create templates if needed
4. Update context store if required
5. Test with orchestration suite

### Modifying Memory System

1. Update relevant module in `src/memory/`
2. Ensure backward compatibility
3. Update migration scripts if needed
4. Test data persistence
5. Update documentation

## Troubleshooting

- Check `cache/logs/errors.log` for errors
- Verify environment variables are set correctly
- Ensure all dependencies are installed
- Check data directory permissions
- Review cost tracker for API limit issues

## Resources

- Installation: `docs/installation_guide.md`
- Quick Start: `QUICKSTART.md`
- Architecture: `ARCHITECTURE.md`
- System Map: `docs/SYSTEM_MAP_COMPLETE.md`
- Worker Architecture: `docs/WORKER_SYSTEM_ARCHITECTURE.MD`

---

**Last Updated**: 2025-10-17