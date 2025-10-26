# HTML Demo Presentation Style Reference

This document defines the styling and structure patterns for HTML presentation demos based on the Salesforce AI demo.

## Reference Files
- **HTML Demo**: `/home/bbrelin/src/repos/salesforce/slides/ai_agent_demo.html`
- **Chart.js Documentation**: `/home/bbrelin/src/repos/salesforce/.agents/agile/chartjs_reference.md`

## Key Characteristics

### 1. Page Structure

**Full-Screen Presentation Container**:
```html
<body>
    <div class="presentation-container">
        <!-- Slides go here -->
        <div class="slide active">...</div>
        <div class="slide">...</div>

        <!-- Navigation controls -->
        <div class="controls">
            <button id="prevBtn">← Previous</button>
            <span class="slide-counter">Slide 1 of 5</span>
            <button id="nextBtn">Next →</button>
        </div>

        <!-- Progress bar -->
        <div class="progress-bar">
            <div class="progress-fill"></div>
        </div>
    </div>
</body>
```

### 2. Visual Design Patterns

**Gradient Backgrounds**:
```css
body {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
```

**Card-Based Layouts**:
- Gradient colored cards for features
- Grid layouts with auto-fit responsiveness
- Hover animations (translateY transform)

**Color Schemes**:
```css
.card.green { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
.card.orange { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
.card.blue { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
.card.yellow { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }
```

### 3. Slide Types

**Title Slide**:
- Large centered heading (48px)
- Subtitle with context
- Grid of feature cards with icons
- Professional gradient color scheme

**Demo Interaction Slide**:
- Split layout: chat interface + process cards
- Animated typing indicators
- Real-time status updates
- Context highlighting in messages

**Dashboard/Analytics Slide**:
- 2-column grid layout
- Chart.js visualizations
- Metric cards with large values
- Comparison tables

**Architecture/System Slide**:
- Grid of agent/component cards
- Icons and descriptions
- Visual flow indicators

**Results/Conclusion Slide**:
- Comparison tables (before/after)
- Key metrics highlighted
- Call-to-action messaging

### 4. Interactive Components

**Chat Interface**:
```html
<div class="chat-container">
    <div class="chat-header">
        💬 AI Agent Conversation
    </div>
    <div class="chat-messages">
        <div class="message user">User message</div>
        <div class="message agent">
            <strong>🤖 Agent Name</strong>
            Response with <span class="context-highlight">highlighted context</span>
        </div>
    </div>
    <div class="typing-indicator active">
        <span></span><span></span><span></span>
    </div>
</div>
```

**Process Status Cards**:
```html
<div class="process-card active">
    <h4>🔍 Step Name</h4>
    <p>Description of what's happening</p>
    <span class="status processing">Processing...</span>
    <!-- or -->
    <span class="status complete">✓ Complete</span>
</div>
```

**Animated Metrics**:
```html
<div class="metric">
    <span class="label">Response Time</span>
    <span class="value green">-40%</span>
</div>
```

### 5. Chart.js Integration

**Loading Chart.js**:
```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
```

**Chart Container Pattern**:
```html
<div class="dashboard-card">
    <h3>📊 Chart Title</h3>
    <canvas id="myChart"></canvas>
</div>
```

**Chart Initialization**:
```javascript
const ctx = document.getElementById('myChart').getContext('2d');
new Chart(ctx, {
    type: 'line', // or 'bar', 'doughnut', etc.
    data: {
        labels: ['Q1', 'Q2', 'Q3', 'Q4'],
        datasets: [{
            label: 'Metric Name',
            data: [65, 70, 80, 90],
            borderColor: '#667eea',
            backgroundColor: 'rgba(102, 126, 234, 0.1)',
            tension: 0.4
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
            legend: { position: 'bottom' }
        }
    }
});
```

### 6. Animation Patterns

**Fade In Animation**:
```css
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}
.message { animation: fadeIn 0.5s ease; }
```

**Typing Indicator**:
```css
@keyframes typing {
    0%, 60%, 100% { transform: translateY(0); }
    30% { transform: translateY(-10px); }
}
.typing-indicator span {
    animation: typing 1.4s infinite;
}
```

**Hover Effects**:
```css
.card:hover { transform: translateY(-5px); }
.controls button:hover {
    background: #5568d3;
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
}
```

### 7. Navigation System

**Slide Controls**:
```javascript
let currentSlide = 0;
const slides = document.querySelectorAll('.slide');
const totalSlides = slides.length;

function showSlide(n) {
    slides[currentSlide].classList.remove('active');
    currentSlide = (n + totalSlides) % totalSlides;
    slides[currentSlide].classList.add('active');
    updateProgress();
}

function updateProgress() {
    const progress = ((currentSlide + 1) / totalSlides) * 100;
    document.querySelector('.progress-fill').style.width = progress + '%';
}
```

**Keyboard Navigation**:
```javascript
document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowRight') showSlide(currentSlide + 1);
    if (e.key === 'ArrowLeft') showSlide(currentSlide - 1);
});
```

### 8. Demo Simulation

**Timed Message Sequence**:
```javascript
function simulateConversation() {
    const messages = [
        { type: 'user', text: 'User question', delay: 0 },
        { type: 'agent', text: 'Agent response', delay: 2000 }
    ];

    messages.forEach(msg => {
        setTimeout(() => {
            addMessage(msg.type, msg.text);
        }, msg.delay);
    });
}
```

**Process State Updates**:
```javascript
function updateProcessStep(step, status) {
    const card = document.getElementById(`step-${step}`);
    card.classList.add('active');
    card.querySelector('.status').textContent = status;
    card.querySelector('.status').className = `status ${status.toLowerCase()}`;
}
```

### 9. Responsive Design

**Container Sizing**:
```css
.presentation-container {
    width: 90vw;
    height: 90vh;
    max-width: 1400px;
}
```

**Grid Layouts**:
```css
.cards-container {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 20px;
}

.dashboard-container {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 30px;
}

@media (max-width: 768px) {
    .dashboard-container {
        grid-template-columns: 1fr;
    }
}
```

### 10. Professional Polish

**Shadows and Depth**:
```css
.card {
    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
}

.presentation-container {
    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
}
```

**Rounded Corners**:
```css
.presentation-container { border-radius: 20px; }
.card { border-radius: 15px; }
.message { border-radius: 15px; }
.controls button { border-radius: 25px; }
```

**Transitions**:
```css
.card { transition: transform 0.3s ease; }
.controls button { transition: all 0.3s ease; }
.progress-fill { transition: width 0.1s linear; }
```

## Best Practices

1. **Performance**:
   - Use CSS animations over JavaScript when possible
   - Lazy-load chart data
   - Minimize DOM manipulations

2. **Accessibility**:
   - Keyboard navigation support
   - Clear focus indicators
   - Semantic HTML structure

3. **Professional Design**:
   - Consistent color palette
   - Professional gradients
   - Adequate whitespace
   - Clear hierarchy

4. **Interactive Elements**:
   - Visual feedback for all interactions
   - Smooth transitions
   - Loading states
   - Error handling

5. **Content Structure**:
   - Clear slide progression
   - Logical information flow
   - Emphasis on key metrics
   - Visual storytelling

## Complete Slide Template

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Demo Title</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        /* Include styles from sections above */
    </style>
</head>
<body>
    <div class="presentation-container">
        <!-- Slide 1: Title -->
        <div class="slide active">
            <div class="slide-header">
                <h1>🚀 Demo Title</h1>
                <p>Compelling subtitle</p>
            </div>
            <div class="cards-container">
                <!-- Feature cards -->
            </div>
        </div>

        <!-- Slide 2: Demo -->
        <div class="slide">
            <!-- Interactive demo content -->
        </div>

        <!-- Slide 3: Analytics -->
        <div class="slide">
            <div class="dashboard-container">
                <!-- Charts and metrics -->
            </div>
        </div>

        <!-- Controls -->
        <div class="controls">
            <button id="prevBtn">← Previous</button>
            <span class="slide-counter">Slide 1 of 3</span>
            <button id="nextBtn">Next →</button>
        </div>

        <div class="progress-bar">
            <div class="progress-fill"></div>
        </div>
    </div>

    <script>
        // Navigation logic
        // Chart initialization
        // Demo simulation
    </script>
</body>
</html>
```

## When to Use HTML Demos vs Jupyter Notebooks

**Use HTML Demos When**:
- Presenting to non-technical audiences
- Live demonstrations with animations
- Slide-based presentations
- Marketing/sales contexts
- Interactive storytelling needed

**Use Jupyter Notebooks When**:
- Technical documentation
- Data analysis workflows
- Code examples and tutorials
- Scientific/research contexts
- Python-centric workflows

## Resources
- Chart.js: https://www.chartjs.org/
- CSS Gradients: https://cssgradient.io/
- MDN Web Docs: https://developer.mozilla.org/
