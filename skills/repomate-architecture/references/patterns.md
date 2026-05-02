# Architectural Pattern Detection Heuristics

## Layered Architecture

**Signature**:
- Directories named by layer: `presentation/`, `application/`, `domain/`, `infrastructure/`
- OR: `controllers/`, `services/`, `repositories/`, `models/`
- One-way dependency flow: outer layers depend on inner layers only
- Each layer has a well-defined interface

**Detection**:
1. Look for `controllers/`, `handlers/`, `views/` directories → presentation layer
2. Look for `services/`, `use_cases/`, `application/` → application layer
3. Look for `models/`, `entities/`, `domain/` → domain layer
4. Look for `repositories/`, `gateways/`, `clients/` → infrastructure layer
5. Verify one-way dependency: infrastructure imports should NOT import from presentation

## Model-View-Controller (MVC)

**Signature**:
- `models/`, `views/`, `controllers/` directories
- Controllers handle routing, models handle data, views handle rendering
- Common in web frameworks (Django, Rails, Laravel, Express MVC)

**Detection**:
1. Check for all three directories
2. Controllers should import from models but not from views
3. Models should have no framework-specific imports (pure domain)

## Plugin / Strategy Pattern

**Signature**:
- Base class or interface (`class BasePlugin`, `Protocol`, ABC)
- Multiple concrete implementations in separate files
- Factory function or registry that selects implementations
- Directory per plugin: `plugins/<name>/`

**Detection**:
1. Search for abstract base classes or Protocols
2. Look for plugin registries: `Registry`, `PluginManager`, `factory.py`
3. Count implementations of the base class — 3+ = plugin architecture
4. Check for configuration-driven plugin loading

## Event-Driven

**Signature**:
- Event bus, message queue, or pub/sub imports
- Event handler registration (`@subscribe`, `on()`, `addListener()`)
- Event classes or message types
- Async processing patterns (workers, consumers)

**Detection**:
1. Search for imports of event/messaging libraries (RabbitMQ, Kafka, Redis pub/sub, EventEmitter)
2. Look for `Event`, `Message`, `Command` class hierarchies
3. Check for `@event_handler` or similar decorators
4. Verify async dispatch → handler pattern

## Hexagonal (Ports & Adapters)

**Signature**:
- `ports/` directory (interfaces/contracts)
- `adapters/` directory (implementations)
- Domain logic has no external framework imports
- Dependency inversion: domain defines interfaces, adapters implement them

**Detection**:
1. Look for `ports/` or `interfaces/` directories
2. Check domain modules — they should import only stdlib
3. Verify that infrastructure imports from domain, not vice versa

## Pipeline / Chain of Responsibility

**Signature**:
- Sequential processing stages
- Each stage transforms data and passes to the next
- Middleware pattern (request → mw1 → mw2 → handler → response)
- Composeable functions/pipes

**Detection**:
1. Look for middleware chains or pipeline configurations
2. Search for `next()` or `chain()` patterns
3. Check for `Pipeline`, `Middleware`, `Handler` class names

## Microkernel

**Signature**:
- Small core (< 20% of code)
- Many extension/plugin directories (> 80% of code)
- Core defines minimal interfaces, extensions implement them
- Extensions are independently loadable

**Detection**:
1. Identify the "core" — the minimal set that everything imports
2. Count extension directories (anything not-core)
3. Core should be < 500 lines
4. Extensions should have no cross-dependencies
