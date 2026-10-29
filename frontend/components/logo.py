"""
NEXUS Visual Identity & Logo System
Provides scalable, original SVG wordmarks and tactical emblem components
featuring the symmetrical crossed-axis 'X' motif.
"""

def get_nexus_logo_svg(size: str = "full", color: str = "#F4F2E9", accent: str = "#B49A5A") -> str:
    """
    Generate original NEXUS vector logo SVG.
    Supports sizes: 'full' (wordmark), 'sidebar' (compact), 'icon' (square), 'favicon'.
    """
    if size == "icon" or size == "favicon":
        dim = 32 if size == "favicon" else 48
        return f"""
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="{dim}" height="{dim}">
            <rect width="64" height="64" rx="8" fill="#183B2B" stroke="#556B2F" stroke-width="2"/>
            <!-- Symmetrical technical crossed-axis motif for X -->
            <line x1="16" y1="16" x2="48" y2="48" stroke="{color}" stroke-width="5" stroke-linecap="round"/>
            <line x1="48" y1="16" x2="16" y2="48" stroke="{color}" stroke-width="5" stroke-linecap="round"/>
            <!-- Center technical crosshair reticle -->
            <circle cx="32" cy="32" r="8" fill="none" stroke="{accent}" stroke-width="2.5"/>
            <circle cx="32" cy="32" r="2.5" fill="{accent}"/>
            <line x1="32" y1="18" x2="32" y2="24" stroke="{accent}" stroke-width="2"/>
            <line x1="32" y1="40" x2="32" y2="46" stroke="{accent}" stroke-width="2"/>
            <line x1="18" y1="32" x2="24" y2="32" stroke="{accent}" stroke-width="2"/>
            <line x1="40" y1="32" x2="46" y2="32" stroke="{accent}" stroke-width="2"/>
        </svg>
        """

    elif size == "sidebar":
        return f"""
        <div style="display: flex; align-items: center; gap: 10px; padding: 4px 0;">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40" width="34" height="34">
                <rect width="40" height="40" rx="6" fill="#183B2B" stroke="#556B2F" stroke-width="1.5"/>
                <line x1="10" y1="10" x2="30" y2="30" stroke="{color}" stroke-width="3.5" stroke-linecap="round"/>
                <line x1="30" y1="10" x2="10" y2="30" stroke="{color}" stroke-width="3.5" stroke-linecap="round"/>
                <circle cx="20" cy="20" r="5" fill="none" stroke="{accent}" stroke-width="1.8"/>
                <circle cx="20" cy="20" r="1.5" fill="{accent}"/>
            </svg>
            <div style="line-height: 1.1;">
                <span style="font-family: var(--font-display, 'Segoe UI', sans-serif); font-weight: 800; font-size: 1.25rem; letter-spacing: 0.12em; color: {color};">NEXUS</span>
                <div style="font-family: var(--font-mono, 'Consolas', monospace); font-size: 0.65rem; color: {accent}; letter-spacing: 0.14em; text-transform: uppercase;">INTELLIGENCE</div>
            </div>
        </div>
        """

    # Full wordmark default
    return f"""
    <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 4px;">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 54 54" width="46" height="46">
            <rect width="54" height="54" rx="8" fill="#183B2B" stroke="#556B2F" stroke-width="2"/>
            <line x1="13" y1="13" x2="41" y2="41" stroke="{color}" stroke-width="4.5" stroke-linecap="round"/>
            <line x1="41" y1="13" x2="13" y2="41" stroke="{color}" stroke-width="4.5" stroke-linecap="round"/>
            <circle cx="27" cy="27" r="7" fill="none" stroke="{accent}" stroke-width="2.2"/>
            <circle cx="27" cy="27" r="2" fill="{accent}"/>
            <line x1="27" y1="14" x2="27" y2="20" stroke="{accent}" stroke-width="1.8"/>
            <line x1="27" y1="34" x2="27" y2="40" stroke="{accent}" stroke-width="1.8"/>
            <line x1="14" y1="27" x2="20" y2="27" stroke="{accent}" stroke-width="1.8"/>
            <line x1="34" y1="27" x2="40" y2="27" stroke="{accent}" stroke-width="1.8"/>
        </svg>
        <div>
            <div style="font-family: var(--font-display, 'Segoe UI', sans-serif); font-weight: 900; font-size: 1.7rem; letter-spacing: 0.15em; color: {color};">
                NE<span style="color: {accent};">X</span>US
            </div>
            <div style="font-family: var(--font-mono, 'Consolas', monospace); font-size: 0.72rem; color: #D6C6A5; letter-spacing: 0.12em; text-transform: uppercase;">
                OFFLINE-FIRST KNOWLEDGE PLATFORM
            </div>
        </div>
    </div>
    """
