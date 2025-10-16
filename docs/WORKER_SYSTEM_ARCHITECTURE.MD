# Knowledge Worker System - Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACE                            │
│                  (CLI / Streamlit)                           │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│              ORCHESTRATOR AGENT                              │
│         (Main AutonomousAgent - Enhanced)                    │
│                                                              │
│  Capabilities:                                               │
│  • Analyze user query                                        │
│  • Decide which workers to spawn                            │
│  • Coordinate worker execution (concurrent)                 │
│  • Aggregate & synthesize results                           │
│  • Maintain conversation context                            │
└────────────┬────────────────────────┬──────────────────────┘
             │                        │
┌────────────▼────────┐    ┌─────────▼──────────┐
│  WORKER REGISTRY    │    │  TEMPLATE ENGINE   │
│                     │    │                     │
│  • Available workers│    │  • Jinja2 templates│
│  • Capabilities     │    │  • Variable injection│
│  • Cost estimates   │    │  • Validation       │
└────────────┬────────┘    └─────────┬──────────┘
             │                       │
             └───────┬───────────────┘
                     │
┌────────────────────▼───────────────────────────────────────┐
│                  WORKER FACTORY                             │
│                                                             │
│  • Spawn workers from templates                            │
│  • Inject context & variables                              │
│  • Configure worker parameters                             │
└────────────┬──────────────┬─────────────┬──────────────────┘
             │              │             │
┌────────────▼─────┐ ┌──────▼──────┐ ┌───▼──────────┐
│  KNOWLEDGE       │ │  KNOWLEDGE  │ │  KNOWLEDGE   │
│  WORKER 1        │ │  WORKER 2   │ │  WORKER 3    │
│                  │ │             │ │              │
│  Menu Planner    │ │Cost Analyst │ │ HR Advisor   │
│  • Recipe ideas  │ │• Budget calc│ │• Hiring tips │
│  • Ingredients   │ │• Pricing    │ │• Training    │
│  • Pairings      │ │• ROI        │ │• Scheduling  │
└──────────────────┘ └─────────────┘ └──────────────┘

┌─────────────────────────────────────────────────────────────┐
│               SHARED CONTEXT STORE                           │
│                                                              │
│  • User profile & preferences                                │
│  • Query analysis results                                    │
│  • Worker outputs                                            │
│  • Conversation history                                      │
│  • Tool results (search, memory, etc.)                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Orchestrator Agent (Enhanced AutonomousAgent)

**Responsibilities:**
- Analyze incoming query
- Determine which workers are needed
- Spawn workers (concurrently via Phase 2)
- Collect and synthesize worker outputs
- Maintain conversation coherence

**New Capabilities:**
```python
- analyze_query_intent()      # What is user asking?
- select_workers()             # Which workers can help?
- spawn_workers()              # Create worker instances
- coordinate_execution()       # Run workers (concurrent)
- synthesize_results()         # Combine outputs
```

---

### 2. Worker Registry

**Purpose**: Catalog of available knowledge workers

**Structure**:
```yaml
workers:
  menu_planner:
    name: "Menu Planning Expert"
    description: "Designs menus, suggests recipes, pairs dishes"
    capabilities:
      - menu_design
      - recipe_development
      - wine_pairing
      - seasonal_planning
    cost_estimate: "medium"
    template: "menu_planner.j2"
    
  cost_analyst:
    name: "Restaurant Cost Analyst"
    description: "Analyzes costs, pricing, margins, ROI"
    capabilities:
      - cost_calculation
      - pricing_strategy
      - margin_analysis
      - budget_planning
    cost_estimate: "low"
    template: "cost_analyst.j2"
    
  operations_expert:
    name: "Restaurant Operations Expert"
    description: "Kitchen workflow, inventory, supplier management"
    capabilities:
      - workflow_optimization
      - inventory_management
      - supplier_negotiation
      - quality_control
    cost_estimate: "medium"
    template: "operations_expert.j2"
```

---

### 3. Template Engine

**Technology**: Jinja2 (already in Python ecosystem)

**Template Structure**:
```jinja2
You are a {{ worker_name }}, an expert in {{ domain }}.

CONTEXT:
- User Type: {{ user_profile.role }}
- Restaurant Type: {{ user_profile.cuisine_type }}
- Query: {{ user_query }}
- Relevant History: {{ conversation_summary }}

YOUR EXPERTISE:
{{ expertise_description }}

CURRENT TASK:
{{ task_description }}

AVAILABLE TOOLS:
{{ available_tools }}

CONSTRAINTS:
- Budget: {{ budget_constraint }}
- Timeline: {{ timeline }}
- Special Requirements: {{ special_requirements }}

Please provide your expert analysis and recommendations.
```

**Variable Types**:
1. **Static** - From template definition
2. **User Context** - From profile/memory
3. **Query-Derived** - Extracted from current query
4. **Dynamic** - Updated during execution
5. **Tool Results** - From tool executions

---

### 4. Worker Factory

**Purpose**: Instantiate workers from templates

**Process**:
```python
1. Load template
2. Gather context
3. Inject variables
4. Create worker instance
5. Configure parameters (model, tokens, etc.)
6. Return ready worker
```

**Worker Instance**:
```python
class KnowledgeWorker:
    def __init__(
        self,
        worker_id: str,
        template: str,
        context: Dict,
        tools: List[str]
    ):
        self.worker_id = worker_id
        self.prompt = render_template(template, context)
        self.tools = tools
        self.results = []
    
    async def execute(self) -> WorkerResult:
        # Run worker's task
        pass
```

---

### 5. Shared Context Store

**Purpose**: Enable workers to share information

**Structure**:
```python
{
    "request_id": "uuid",
    "user_id": "user_123",
    "user_profile": {...},
    "query": {
        "original": "How can I reduce food costs?",
        "intent": "cost_optimization",
        "entities": ["food_costs"],
        "sentiment": "concerned"
    },
    "workers_spawned": [
        {
            "worker_id": "cost_analyst_001",
            "status": "complete",
            "output": {...}
        }
    ],
    "tool_results": [...],
    "conversation_summary": "..."
}
```

---

## Data Flow

### Query Processing Flow

```
1. User Query
   ↓
2. Orchestrator: Analyze Intent
   - Extract entities
   - Identify domain
   - Assess complexity
   ↓
3. Orchestrator: Select Workers
   - Match capabilities to intent
   - Consider cost/time trade-offs
   - Determine execution order
   ↓
4. Worker Factory: Spawn Workers
   - Load templates
   - Inject context
   - Configure parameters
   ↓
5. Workers: Execute (Concurrently)
   - Run specialized analysis
   - Use tools if needed
   - Generate results
   ↓
6. Orchestrator: Synthesize
   - Combine outputs
   - Resolve conflicts
   - Format response
   ↓
7. Response to User
```

---

## Worker Types (Restaurant Focus)

### Core Workers

1. **Menu Planner**
   - Menu design & optimization
   - Recipe development
   - Seasonal planning
   - Dietary accommodations

2. **Cost Analyst**
   - Food cost analysis
   - Pricing strategies
   - Margin optimization
   - Budget planning

3. **Operations Expert**
   - Kitchen workflow
   - Inventory management
   - Staff scheduling
   - Quality control

4. **Marketing Strategist**
   - Promotion ideas
   - Social media content
   - Event planning
   - Customer retention

5. **HR Advisor**
   - Hiring strategies
   - Training programs
   - Team management
   - Conflict resolution

6. **Compliance Specialist**
   - Health regulations
   - Safety protocols
   - Licensing requirements
   - Documentation

### Specialized Workers

7. **Wine Sommelier**
   - Wine pairing
   - Beverage program
   - Supplier recommendations

8. **Pastry Chef**
   - Dessert menu
   - Baking techniques
   - Presentation ideas

9. **Sustainability Advisor**
   - Waste reduction
   - Local sourcing
   - Energy efficiency

10. **Data Analyst**
    - Sales analytics
    - Trend analysis
    - Performance metrics

---

## Execution Strategies

### Strategy 1: Sequential (Simple)
```
Query → Worker 1 → Worker 2 → Worker 3 → Synthesis
```
- **Pros**: Simple, predictable
- **Cons**: Slow, no parallelism

### Strategy 2: Concurrent (Phase 2)
```
Query → [Worker 1, Worker 2, Worker 3] → Synthesis
```
- **Pros**: Fast, leverages Phase 2
- **Cons**: Workers can't build on each other

### Strategy 3: Hierarchical (Advanced)
```
Query → Primary Worker
          ↓
        [Sub-Worker 1, Sub-Worker 2]
          ↓
        Synthesis
```
- **Pros**: Deep analysis, workers can collaborate
- **Cons**: Complex, slower

### Strategy 4: Adaptive (Recommended)
```
Query → Analyze Complexity
          ↓
    Simple? → Single Worker
    Complex? → Multiple Workers (concurrent)
    Very Complex? → Hierarchical
```
- **Pros**: Optimal for each query
- **Cons**: Requires good heuristics

---

## Cost Optimization

### Worker Tiers

**Tier 1: Light** (Fast, cheap)
- Model: gpt-4o-mini
- Max tokens: 500
- Use for: Simple queries, quick analysis

**Tier 2: Standard** (Balanced)
- Model: gpt-4o
- Max tokens: 1500
- Use for: Most queries

**Tier 3: Deep** (Thorough, expensive)
- Model: gpt-4o
- Max tokens: 4000
- Use for: Complex analysis, reports

### Cost Control

1. **Budget Checking**: Before spawning workers
2. **Smart Caching**: Reuse worker results
3. **Graceful Degradation**: Fewer workers if budget low
4. **User Control**: Let users choose thoroughness level

---

## Error Handling

### Worker Failures

```python
if worker.status == "failed":
    # Try recovery
    1. Retry with different prompt
    2. Fall back to simpler worker
    3. Continue with other workers
    4. Inform user of limitation
```

### Partial Success

```python
if some_workers_succeeded:
    # Synthesize available results
    response = "Based on available analysis..."
    # Note missing perspectives
    "Note: Could not complete [X] analysis"
```

---

## Integration with Existing System

### Minimal Changes Needed

✅ **Existing Infrastructure Used**:
- Async architecture (ready for concurrent workers)
- Tool system (workers can use tools)
- Cost tracking (extend for worker costs)
- Memory system (context store)
- Phase 2 concurrent execution (perfect for workers!)

### New Components Required

1. **Worker Registry** (new file)
2. **Template Engine** (new file)
3. **Worker Factory** (new file)
4. **Orchestrator Enhancement** (modify existing)
5. **Template Library** (new directory)

---

## Performance Expectations

### Without Workers (Current)
- Simple query: 2-3s
- Complex query (3 tools): 2-3s (Phase 2 concurrent)

### With Workers
- Simple query + 1 worker: 3-4s
- Complex query + 3 workers (concurrent): 4-5s
- Very complex + 5 workers (concurrent): 6-7s

**Impact**: +1-3s per query (acceptable for better quality)

---

## Extensibility

### Easy to Add New Workers

1. Create template file
2. Add to registry
3. Done!

No code changes needed for new worker types.

### Easy to Modify Workers

1. Edit template
2. Test with sample queries
3. Deploy

Version control handles rollbacks.

---

## Testing Strategy

### Unit Tests
- Template rendering
- Variable injection
- Worker spawning

### Integration Tests
- Orchestrator → Worker → Results
- Concurrent worker execution
- Context sharing

### End-to-End Tests
- Full query flows
- Multiple worker scenarios
- Error conditions

---

## Monitoring & Observability

### Metrics to Track

1. **Worker Usage**
   - Which workers most used?
   - Success rates per worker
   - Average execution time

2. **Cost Tracking**
   - Cost per worker type
   - Total vs single-agent cost
   - ROI (quality improvement vs cost)

3. **Performance**
   - Latency impact
   - Concurrent execution efficiency
   - Cache hit rates

4. **Quality**
   - User satisfaction
   - Response completeness
   - Worker agreement/conflicts

---

## Rollout Strategy

### Phase 1: Foundation (Week 1)
- Implement worker registry
- Add template engine
- Create worker factory
- Build 2-3 core workers

### Phase 2: Integration (Week 2)
- Enhance orchestrator
- Add context store
- Enable concurrent execution
- Testing

### Phase 3: Expansion (Week 3-4)
- Add more workers
- Optimize templates
- Tune performance
- User feedback

### Phase 4: Advanced (Month 2)
- Hierarchical workers
- Worker-to-worker communication
- Advanced caching
- Analytics dashboard

---

## Success Criteria

✅ System is successful if:

1. **Quality**: Responses are more comprehensive
2. **Specialization**: Workers show clear expertise
3. **Performance**: <5s for most queries
4. **Cost**: <2x increase vs single-agent
5. **Reliability**: 95%+ success rate
6. **Usability**: Easy to add new workers

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| High costs | High | Tiered workers, budget controls |
| Slow responses | Medium | Concurrent execution, caching |
| Complexity | Medium | Clear architecture, good docs |
| Worker conflicts | Low | Synthesis logic, validation |
| Debugging difficulty | Medium | Request IDs, detailed logging |

---

## Recommendation

**PROCEED** with this implementation!

**Why**:
- Aligns perfectly with restaurant consulting domain
- Leverages existing Phase 2 concurrent execution
- Clear benefit for complex queries
- Extensible architecture
- Manageable complexity

**Start With**:
1. 3-4 core workers (menu, cost, operations, HR)
2. Simple concurrent execution
3. Measure quality improvement
4. Iterate based on usage patterns

**Expected Outcome**:
More comprehensive, expert-level responses while maintaining good performance.

---

*Architecture designed for CapeTownConsultant v3.2*  
*Status: Ready for Implementation*