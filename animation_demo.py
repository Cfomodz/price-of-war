import asyncio
import logging
import random
import sys
from datetime import datetime
from animation_manager import (
    get_animation_manager, 
    close_animation_manager, 
    AnimationProps, 
    EasingType
)
from logging_config import setup_logging
from user_rep import UserStats, UserManager

# Initialize logging
logger = setup_logging()

class AnimationVisualizer:
    """Simple console visualizer for animations"""
    
    CHARS = " ▁▂▃▄▅▆▇█"  # Characters for visualization from empty to full
    
    @staticmethod
    def visualize_value(value: float, width: int = 50) -> str:
        """Visualize a 0-1 value as a bar"""
        clamped = min(1.0, max(0.0, value))
        filled = int(width * clamped)
        return "[" + "█" * filled + " " * (width - filled) + f"] {clamped:.2f}"
    
    @staticmethod
    def visualize_position(x: float, y: float, width: int = 20, height: int = 10) -> str:
        """Visualize a position as a 2D grid"""
        grid = [[" " for _ in range(width)] for _ in range(height)]
        
        # Clamp x and y to grid bounds
        grid_x = min(width - 1, max(0, int(x * width)))
        grid_y = min(height - 1, max(0, int(y * height)))
        
        # Place marker
        grid[grid_y][grid_x] = "●"
        
        # Build the string representation
        output = f"Position: ({x:.2f}, {y:.2f})\n"
        for row in grid:
            output += "|" + "".join(row) + "|\n"
        
        return output
    
    @staticmethod
    def visualize_color(r: float, g: float, b: float) -> str:
        """Visualize a color as RGB bars"""
        r_bar = AnimationVisualizer.visualize_value(r, 20)
        g_bar = AnimationVisualizer.visualize_value(g, 20)
        b_bar = AnimationVisualizer.visualize_value(b, 20)
        
        hex_color = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
        
        return f"Color: {hex_color}\nR: {r_bar}\nG: {g_bar}\nB: {b_bar}"

class ConsoleAnimationHandler:
    """Handler for displaying animations in the console"""
    
    def __init__(self):
        self.values = {}
        self.visualizer = AnimationVisualizer
        
    async def handle_opacity(self, target_id: str, _: str, value: float):
        """Handle opacity animation updates"""
        self.values[f"{target_id}:opacity"] = value
        print(f"\n{target_id} Opacity:")
        print(self.visualizer.visualize_value(value))
        
    async def handle_scale(self, target_id: str, _: str, value: float):
        """Handle scale animation updates"""
        self.values[f"{target_id}:scale"] = value
        print(f"\n{target_id} Scale:")
        print(self.visualizer.visualize_value(value / 2.0))  # Scale can go > 1, so divide
        
    async def handle_position(self, target_id: str, _: str, value: tuple):
        """Handle position animation updates"""
        x, y = value
        self.values[f"{target_id}:position"] = value
        print(f"\n{target_id} Position:")
        print(self.visualizer.visualize_position(x, y))
        
    async def handle_color(self, target_id: str, _: str, value: tuple):
        """Handle color animation updates"""
        r, g, b = value
        self.values[f"{target_id}:color"] = value
        print(f"\n{target_id} Color:")
        print(self.visualizer.visualize_color(r, g, b))

async def run_simple_demo():
    """Run a simple animation demo using console visualization"""
    # Get animation manager
    animation_manager = get_animation_manager()
    await animation_manager.start()
    
    # Create handler
    handler = ConsoleAnimationHandler()
    
    # Register callbacks
    animation_manager.register_animation_callback("demo_object", "opacity", handler.handle_opacity)
    animation_manager.register_animation_callback("demo_object", "scale", handler.handle_scale)
    animation_manager.register_animation_callback("demo_object", "position", handler.handle_position)
    animation_manager.register_animation_callback("demo_object", "color", handler.handle_color)
    
    # Print instructions
    print("Animation Demo - Console Visualization")
    print("--------------------------------------")
    print("This demo shows animation capabilities with console visualization")
    print("Press Ctrl+C to exit at any time")
    
    try:
        # Fade Demo
        print("\n\nFade Demo")
        print("=========")
        await animation_manager.fade(
            target_id="demo_object",
            start_opacity=0.0,
            end_opacity=1.0,
            duration_ms=2000,
            easing=EasingType.LINEAR
        )
        
        # Short pause between demos
        await asyncio.sleep(0.5)
        
        # Scale Demo
        print("\n\nScale Demo")
        print("==========")
        await animation_manager.scale(
            target_id="demo_object",
            start_scale=1.0,
            end_scale=2.0,
            duration_ms=2000,
            easing=EasingType.BOUNCE
        )
        
        # Short pause between demos
        await asyncio.sleep(0.5)
        
        # Position Demo
        print("\n\nPosition Demo")
        print("=============")
        await animation_manager.move(
            target_id="demo_object",
            start_pos=(0.0, 0.0),
            end_pos=(1.0, 1.0),
            duration_ms=3000,
            easing=EasingType.EASE_IN_OUT
        )
        
        # Short pause between demos
        await asyncio.sleep(0.5)
        
        # Color Demo
        print("\n\nColor Demo")
        print("==========")
        await animation_manager.color(
            target_id="demo_object",
            start_color=(1.0, 0.0, 0.0),  # Red
            end_color=(0.0, 0.0, 1.0),    # Blue
            duration_ms=3000,
            easing=EasingType.LINEAR
        )
        
        # Short pause between demos
        await asyncio.sleep(0.5)
        
        # Sequence Demo
        print("\n\nSequence Demo")
        print("=============")
        
        animations = [
            AnimationProps(
                target_id="demo_object",
                property_name="opacity",
                start_value=1.0,
                end_value=0.2,
                duration_ms=800,
                easing=EasingType.EASE_IN
            ),
            AnimationProps(
                target_id="demo_object",
                property_name="scale",
                start_value=1.0,
                end_value=1.5,
                duration_ms=1000,
                easing=EasingType.BOUNCE
            ),
            AnimationProps(
                target_id="demo_object",
                property_name="opacity",
                start_value=0.2,
                end_value=1.0,
                duration_ms=800,
                easing=EasingType.EASE_OUT
            )
        ]
        
        await animation_manager.sequence(animations, gap_ms=200)
        
        # Demo complete
        print("\n\nDemo Complete!")
        print("==============")
        print("Thanks for watching the animation demo")
            
    except asyncio.CancelledError:
        print("\nDemo cancelled")
    finally:
        # Clean up
        await close_animation_manager()

async def run_obs_style_demo():
    """Run a demo that simulates the OBS controller's animation style"""
    # Get animation manager
    animation_manager = get_animation_manager()
    await animation_manager.start()
    
    # Create handler
    handler = ConsoleAnimationHandler()
    
    # Register callbacks for UI elements
    ui_elements = {
        "up_arrow": "up_arrow_element",
        "down_arrow": "down_arrow_element",
        "set_indicator": "set_indicator_element",
        "nice_glow": "nice_glow_element",
        "user_display": "user_display_element"
    }
    
    for element_id in ui_elements.values():
        animation_manager.register_animation_callback(
            element_id, "opacity", handler.handle_opacity
        )
        animation_manager.register_animation_callback(
            element_id, "scale", handler.handle_scale
        )
        animation_manager.register_animation_callback(
            element_id, "color", handler.handle_color
        )
    
    # Create a fake user
    user = UserStats(
        user_id="demo_user",
        lifetime_votes=100,
        show_votes=20,
        nice_status={"lifetime": True, "show": True}
    )
    
    # Print instructions
    print("OBS-Style Animation Demo")
    print("=======================")
    print("This demo simulates the animations used in the OBS controller")
    print("Press Ctrl+C to exit at any time")
    
    try:
        # Simulate an "up" vote effect
        print("\n\nSimulating UP vote effect")
        print("==========================")
        
        # Arrow animation
        arrow_element = ui_elements["up_arrow"]
        intensity = 0.8
        
        # 1. Fade in arrow
        await animation_manager.fade(
            target_id=arrow_element,
            start_opacity=0.0,
            end_opacity=1.0,
            duration_ms=200,
            easing=EasingType.EASE_OUT
        )
        
        # 2. Scale up arrow
        await animation_manager.scale(
            target_id=arrow_element,
            start_scale=1.0,
            end_scale=1.0 + (intensity * 0.5),
            duration_ms=300,
            easing=EasingType.BOUNCE
        )
        
        # 3. Show nice glow
        nice_element = ui_elements["nice_glow"]
        await animation_manager.fade(
            target_id=nice_element,
            start_opacity=0.0,
            end_opacity=0.7,
            duration_ms=500,
            easing=EasingType.EASE_IN_OUT
        )
        
        # 4. Show user display
        user_element = ui_elements["user_display"]
        await animation_manager.fade(
            target_id=user_element,
            start_opacity=0.0,
            end_opacity=0.9,
            duration_ms=300,
            easing=EasingType.EASE_OUT
        )
        
        # 5. Fade out arrow after a delay
        await animation_manager.fade(
            target_id=arrow_element,
            start_opacity=1.0,
            end_opacity=0.0,
            duration_ms=300,
            delay_ms=500,
            easing=EasingType.EASE_IN
        )
        
        # 6. Fade out nice glow
        await animation_manager.fade(
            target_id=nice_element,
            start_opacity=0.7,
            end_opacity=0.0,
            duration_ms=500,
            delay_ms=800,
            easing=EasingType.EASE_IN
        )
        
        # 7. Fade out user display last
        await animation_manager.fade(
            target_id=user_element,
            start_opacity=0.9,
            end_opacity=0.0,
            duration_ms=500,
            delay_ms=1000,
            easing=EasingType.EASE_IN
        )
        
        # Wait for animations to complete
        await asyncio.sleep(2)
        
        # Simulate a "set" vote effect
        print("\n\nSimulating SET vote effect")
        print("==========================")
        
        # Set indicator animation
        set_element = ui_elements["set_indicator"]
        
        # 1. Fade in
        await animation_manager.fade(
            target_id=set_element,
            start_opacity=0.0,
            end_opacity=1.0,
            duration_ms=300,
            easing=EasingType.EASE_OUT
        )
        
        # 2. Color pulse
        await animation_manager.color(
            target_id=set_element,
            start_color=(0.7, 0.7, 0.1),  # Yellow-ish
            end_color=(1.0, 0.8, 0.0),    # Golden
            duration_ms=1000,
            easing=EasingType.EASE_IN_OUT
        )
        
        # 3. Fade out
        await animation_manager.fade(
            target_id=set_element,
            start_opacity=1.0,
            end_opacity=0.0,
            duration_ms=500,
            delay_ms=1200,
            easing=EasingType.EASE_IN
        )
        
        # Wait for animations to complete
        await asyncio.sleep(2)
        
        # Demo complete
        print("\n\nDemo Complete!")
        print("==============")
        print("Thanks for watching the OBS animation demo")
            
    except asyncio.CancelledError:
        print("\nDemo cancelled")
    finally:
        # Clean up
        await close_animation_manager()

async def main():
    """Main entry point for the animation demo"""
    try:
        # Parse arguments
        if len(sys.argv) > 1 and sys.argv[1] == "obs":
            await run_obs_style_demo()
        else:
            await run_simple_demo()
    except KeyboardInterrupt:
        print("\nDemo terminated by user")
    except Exception as e:
        logger.error(f"Error in animation demo: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main()) 