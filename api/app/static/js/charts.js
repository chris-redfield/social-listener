/**
 * Social Listener - Chart Configurations
 * Uses Plotly.js for interactive charts
 */

// Color palette
const COLORS = {
    positive: '#28a745',
    negative: '#dc3545',
    neutral: '#6c757d',
    primary: '#0d6efd',
    info: '#0dcaf0',
    warning: '#ffc107',
    bluesky: '#0085ff'
};

// Default Plotly layout options
const DEFAULT_LAYOUT = {
    margin: { t: 30, r: 20, b: 40, l: 50 },
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { family: 'system-ui, -apple-system, sans-serif' }
};

/**
 * Render sentiment pie chart
 */
function renderSentimentChart(data) {
    if (!data || data.length === 0) {
        document.getElementById('sentiment-chart').innerHTML =
            '<div class="text-center text-muted py-5">No sentiment data available</div>';
        return;
    }

    const labels = data.map(d => capitalize(d.label));
    const values = data.map(d => d.count);
    const colors = data.map(d => COLORS[d.label] || COLORS.neutral);

    const trace = {
        values: values,
        labels: labels,
        type: 'pie',
        hole: 0.4,
        marker: { colors: colors },
        textinfo: 'label+percent',
        textposition: 'outside',
        hovertemplate: '%{label}: %{value} posts<br>%{percent}<extra></extra>'
    };

    const layout = {
        ...DEFAULT_LAYOUT,
        showlegend: true,
        legend: { orientation: 'h', y: -0.1 }
    };

    Plotly.newPlot('sentiment-chart', [trace], layout, { responsive: true });
}

/**
 * Render timeline bar chart
 */
function renderTimelineChart(data) {
    if (!data || data.length === 0) {
        document.getElementById('timeline-chart').innerHTML =
            '<div class="text-center text-muted py-5">No timeline data available</div>';
        return;
    }

    const dates = data.map(d => formatDate(d.date));

    const traces = [
        {
            x: dates,
            y: data.map(d => d.sentiment_positive || 0),
            name: 'Positive',
            type: 'bar',
            marker: { color: COLORS.positive }
        },
        {
            x: dates,
            y: data.map(d => d.sentiment_neutral || 0),
            name: 'Neutral',
            type: 'bar',
            marker: { color: COLORS.neutral }
        },
        {
            x: dates,
            y: data.map(d => d.sentiment_negative || 0),
            name: 'Negative',
            type: 'bar',
            marker: { color: COLORS.negative }
        }
    ];

    const layout = {
        ...DEFAULT_LAYOUT,
        barmode: 'stack',
        xaxis: { title: '' },
        yaxis: { title: 'Posts' },
        legend: { orientation: 'h', y: 1.1 }
    };

    Plotly.newPlot('timeline-chart', traces, layout, { responsive: true });
}

/**
 * Render top authors horizontal bar chart
 */
function renderAuthorsChart(data) {
    if (!data || data.length === 0) {
        document.getElementById('authors-chart').innerHTML =
            '<div class="text-center text-muted py-5">No author data available</div>';
        return;
    }

    // Reverse to show highest at top
    const reversed = [...data].reverse();

    const trace = {
        y: reversed.map(d => truncate(d.author_display_name || d.author_handle, 20)),
        x: reversed.map(d => d.post_count),
        type: 'bar',
        orientation: 'h',
        marker: { color: COLORS.bluesky },
        hovertemplate: '%{y}<br>Posts: %{x}<extra></extra>'
    };

    const layout = {
        ...DEFAULT_LAYOUT,
        margin: { ...DEFAULT_LAYOUT.margin, l: 120 },
        xaxis: { title: 'Posts' },
        yaxis: { title: '' }
    };

    Plotly.newPlot('authors-chart', [trace], layout, { responsive: true });
}

/**
 * Render entity type distribution chart
 */
function renderEntityTypesChart(data, elementId = 'entity-types-chart') {
    if (!data || data.length === 0) {
        document.getElementById(elementId).innerHTML =
            '<div class="text-center text-muted py-5">No entity data available</div>';
        return;
    }

    const trace = {
        values: data.map(d => d.count),
        labels: data.map(d => d.entity_type),
        type: 'pie',
        marker: {
            colors: ['#1976d2', '#7b1fa2', '#388e3c', '#f57c00', '#455a64']
        },
        textinfo: 'label+value'
    };

    const layout = {
        ...DEFAULT_LAYOUT,
        showlegend: false
    };

    Plotly.newPlot(elementId, [trace], layout, { responsive: true });
}

// Utility functions
function capitalize(str) {
    return str ? str.charAt(0).toUpperCase() + str.slice(1) : '';
}

function truncate(str, maxLength) {
    if (!str) return '';
    return str.length > maxLength ? str.substring(0, maxLength) + '...' : str;
}

function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}
