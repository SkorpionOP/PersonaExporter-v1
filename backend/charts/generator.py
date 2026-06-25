import matplotlib.pyplot as plt
import io
import base64
from models.domain import Conversation

def generate_activity_heatmap(conversation: Conversation) -> str:
    """Generates an activity heatmap chart and returns it as a base64 string."""
    # Placeholder for heatmap generation
    fig, ax = plt.subplots(figsize=(8, 4))
    
    # Just a dummy plot for now
    ax.plot([1, 2, 3], [10, 20, 15], marker='o')
    ax.set_title("Activity over time")
    ax.set_xlabel("Time")
    ax.set_ylabel("Messages")
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    return img_str
