import asyncio
import time
import math
import logging
from typing import Dict, List, Callable, Any, Optional, Tuple, Union, Awaitable
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

# Configure logger
logger = logging.getLogger("animation_manager")

class EasingType(Enum):
    """Easing function types for animations"""
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    BOUNCE = "bounce"
    ELASTIC = "elastic"
    BACK = "back"

@dataclass
class AnimationProps:
    """Properties for an animation"""
    target_id: str
    property_name: str
    start_value: Union[float, Tuple[float, ...]]  # Can be single value or tuple for properties like color (r,g,b)
    end_value: Union[float, Tuple[float, ...]]
    duration_ms: int
    delay_ms: int = 0
    easing: EasingType = EasingType.LINEAR
    loop: bool = False
    loop_count: int = 0  # 0 means infinite
    on_complete: Optional[Callable[[], Awaitable[None]]] = None
    
    def __post_init__(self):
        # Ensure start and end values have the same format
        if isinstance(self.start_value, tuple) and isinstance(self.end_value, tuple):
            if len(self.start_value) != len(self.end_value):
                raise ValueError(f"Start value {self.start_value} and end value {self.end_value} must have the same number of elements")
        elif isinstance(self.start_value, tuple) or isinstance(self.end_value, tuple):
            raise ValueError(f"Start value {self.start_value} and end value {self.end_value} must have the same type")

class AnimationState(Enum):
    """State of an animation"""
    PENDING = "pending"
    DELAYED = "delayed"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class Animation:
    """Represents a single animation instance"""
    def __init__(self, props: AnimationProps):
        self.props = props
        self.state = AnimationState.PENDING
        self.start_time: Optional[float] = None
        self.delay_task: Optional[asyncio.Task] = None
        self.animation_task: Optional[asyncio.Task] = None
        self.current_loop = 0
        self.current_value = self.props.start_value
        
    async def start(self):
        """Start the animation"""
        if self.state == AnimationState.RUNNING:
            return
            
        self.state = AnimationState.PENDING
        
        # Handle delay if specified
        if self.props.delay_ms > 0:
            self.state = AnimationState.DELAYED
            await asyncio.sleep(self.props.delay_ms / 1000)
            
        self.state = AnimationState.RUNNING
        self.start_time = time.time()
        
    def calculate_current_value(self, progress: float) -> Union[float, Tuple[float, ...]]:
        """Calculate the current value based on progress and easing function"""
        # Apply easing function to the progress
        eased_progress = self._apply_easing(progress)
        
        # Calculate the current value
        if isinstance(self.props.start_value, tuple) and isinstance(self.props.end_value, tuple):
            # Calculate each component separately for tuple values (like colors)
            return tuple(
                self._interpolate_value(self.props.start_value[i], self.props.end_value[i], eased_progress)
                for i in range(len(self.props.start_value))
            )
        else:
            # For single value
            return self._interpolate_value(self.props.start_value, self.props.end_value, eased_progress)
    
    def _interpolate_value(self, start: float, end: float, progress: float) -> float:
        """Interpolate between start and end values based on progress"""
        return start + (end - start) * progress
    
    def _apply_easing(self, progress: float) -> float:
        """Apply easing function to progress value"""
        if self.props.easing == EasingType.LINEAR:
            return progress
        elif self.props.easing == EasingType.EASE_IN:
            return progress * progress
        elif self.props.easing == EasingType.EASE_OUT:
            return 1 - (1 - progress) * (1 - progress)
        elif self.props.easing == EasingType.EASE_IN_OUT:
            return 0.5 * (math.sin((progress - 0.5) * math.pi) + 1)
        elif self.props.easing == EasingType.BOUNCE:
            if progress < (1 / 2.75):
                return 7.5625 * progress * progress
            elif progress < (2 / 2.75):
                progress -= (1.5 / 2.75)
                return 7.5625 * progress * progress + 0.75
            elif progress < (2.5 / 2.75):
                progress -= (2.25 / 2.75)
                return 7.5625 * progress * progress + 0.9375
            else:
                progress -= (2.625 / 2.75)
                return 7.5625 * progress * progress + 0.984375
        elif self.props.easing == EasingType.ELASTIC:
            return math.sin(13 * math.pi/2 * progress) * math.pow(2, 10 * (progress - 1))
        elif self.props.easing == EasingType.BACK:
            s = 1.70158
            return progress * progress * ((s + 1) * progress - s)
        return progress
    
    def get_progress(self) -> float:
        """Get the current progress of the animation (0.0 to 1.0)"""
        if self.state != AnimationState.RUNNING or self.start_time is None:
            return 0.0
            
        elapsed = (time.time() - self.start_time) * 1000  # Convert to ms
        progress = min(elapsed / self.props.duration_ms, 1.0)
        return progress
    
    async def cancel(self):
        """Cancel the animation"""
        if self.delay_task and not self.delay_task.done():
            self.delay_task.cancel()
            
        if self.animation_task and not self.animation_task.done():
            self.animation_task.cancel()
            
        self.state = AnimationState.CANCELLED
    
    def is_complete(self) -> bool:
        """Check if the animation is complete"""
        return self.state == AnimationState.COMPLETED or self.state == AnimationState.CANCELLED
    
    def should_continue_loop(self) -> bool:
        """Check if the animation should continue looping"""
        if not self.props.loop:
            return False
            
        if self.props.loop_count == 0:  # Infinite loop
            return True
            
        return self.current_loop < self.props.loop_count

class AnimationGroup:
    """Group of animations that can be controlled together"""
    def __init__(self, name: str):
        self.name = name
        self.animations: List[Animation] = []
        self.task: Optional[asyncio.Task] = None
        self.is_running = False
        
    def add_animation(self, animation: Animation):
        """Add an animation to the group"""
        self.animations.append(animation)
        
    async def start(self):
        """Start all animations in the group"""
        self.is_running = True
        await asyncio.gather(*[anim.start() for anim in self.animations])
    
    async def cancel(self):
        """Cancel all animations in the group"""
        self.is_running = False
        await asyncio.gather(*[anim.cancel() for anim in self.animations])
    
    def is_complete(self) -> bool:
        """Check if all animations in the group are complete"""
        return all(anim.is_complete() for anim in self.animations)

class AnimationManager:
    """Manager for all animations in the application"""
    def __init__(self, update_rate_hz: int = 60):
        self.running_animations: Dict[str, Animation] = {}
        self.animation_groups: Dict[str, AnimationGroup] = {}
        self.animation_callbacks: Dict[str, Callable[[str, str, Union[float, Tuple[float, ...]]], Awaitable[None]]] = {}
        self.update_rate_hz = update_rate_hz
        self.update_task: Optional[asyncio.Task] = None
        self.is_running = False
        self.logger = logger
        
    async def start(self):
        """Start the animation manager"""
        if self.is_running:
            return
            
        self.is_running = True
        self.update_task = asyncio.create_task(self._update_loop())
        
    async def stop(self):
        """Stop the animation manager"""
        self.is_running = False
        
        # Cancel all running animations
        for animation_id, animation in list(self.running_animations.items()):
            await animation.cancel()
            del self.running_animations[animation_id]
        
        # Cancel all animation groups
        for group_name, group in list(self.animation_groups.items()):
            await group.cancel()
            del self.animation_groups[group_name]
            
        # Cancel update task
        if self.update_task and not self.update_task.done():
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
    
    async def _update_loop(self):
        """Main update loop for animations"""
        try:
            while self.is_running:
                update_start = time.time()
                
                # Process all running animations
                await self._process_animations()
                
                # Calculate time to sleep to maintain update rate
                elapsed = time.time() - update_start
                sleep_time = max(0, (1 / self.update_rate_hz) - elapsed)
                
                # Sleep until next update
                await asyncio.sleep(sleep_time)
        except asyncio.CancelledError:
            self.logger.info("Animation update loop cancelled")
        except Exception as e:
            self.logger.error(f"Error in animation update loop: {str(e)}", exc_info=True)
    
    async def _process_animations(self):
        """Process all running animations"""
        # Process animations
        to_remove = []
        
        for animation_id, animation in self.running_animations.items():
            if animation.state == AnimationState.RUNNING:
                progress = animation.get_progress()
                
                # Calculate current value based on progress
                animation.current_value = animation.calculate_current_value(progress)
                
                # Call the callback for this target/property
                await self._call_animation_callback(
                    animation.props.target_id, 
                    animation.props.property_name, 
                    animation.current_value
                )
                
                # Check if animation is complete
                if progress >= 1.0:
                    if animation.should_continue_loop():
                        # Reset for next loop
                        animation.start_time = time.time()
                        animation.current_loop += 1
                    else:
                        animation.state = AnimationState.COMPLETED
                        
                        # Call on_complete callback if provided
                        if animation.props.on_complete:
                            try:
                                await animation.props.on_complete()
                            except Exception as e:
                                self.logger.error(f"Error in animation completion callback: {str(e)}")
                        
                        to_remove.append(animation_id)
        
        # Remove completed animations
        for animation_id in to_remove:
            del self.running_animations[animation_id]
    
    async def _call_animation_callback(self, target_id: str, property_name: str, value: Union[float, Tuple[float, ...]]):
        """Call the appropriate callback for an animation update"""
        callback_key = f"{target_id}:{property_name}"
        
        if callback_key in self.animation_callbacks:
            try:
                await self.animation_callbacks[callback_key](target_id, property_name, value)
            except Exception as e:
                self.logger.error(f"Error in animation callback for {callback_key}: {str(e)}")
    
    def register_animation_callback(self, target_id: str, property_name: str, 
                                  callback: Callable[[str, str, Union[float, Tuple[float, ...]]], Awaitable[None]]):
        """Register a callback for animation updates"""
        callback_key = f"{target_id}:{property_name}"
        self.animation_callbacks[callback_key] = callback
    
    def create_animation(self, animation_id: str, props: AnimationProps) -> Animation:
        """Create a new animation"""
        animation = Animation(props)
        self.running_animations[animation_id] = animation
        return animation
    
    async def start_animation(self, animation_id: str, props: AnimationProps) -> str:
        """Create and start a new animation"""
        # Generate an ID if not provided
        if not animation_id:
            animation_id = f"anim_{len(self.running_animations)}_{time.time_ns()}"
            
        # Create the animation
        animation = self.create_animation(animation_id, props)
        
        # Start the animation
        await animation.start()
        
        return animation_id
    
    async def cancel_animation(self, animation_id: str) -> bool:
        """Cancel a running animation"""
        if animation_id in self.running_animations:
            await self.running_animations[animation_id].cancel()
            del self.running_animations[animation_id]
            return True
        return False
    
    def create_animation_group(self, group_name: str) -> AnimationGroup:
        """Create a new animation group"""
        group = AnimationGroup(group_name)
        self.animation_groups[group_name] = group
        return group
    
    async def start_animation_group(self, group_name: str) -> bool:
        """Start an animation group"""
        if group_name in self.animation_groups:
            await self.animation_groups[group_name].start()
            return True
        return False
    
    async def cancel_animation_group(self, group_name: str) -> bool:
        """Cancel an animation group"""
        if group_name in self.animation_groups:
            await self.animation_groups[group_name].cancel()
            del self.animation_groups[group_name]
            return True
        return False
    
    # Utility methods for common animations
    
    async def fade(self, target_id: str, start_opacity: float, end_opacity: float, 
                 duration_ms: int, delay_ms: int = 0, easing: EasingType = EasingType.LINEAR) -> str:
        """Create a fade animation"""
        props = AnimationProps(
            target_id=target_id,
            property_name="opacity",
            start_value=start_opacity,
            end_value=end_opacity,
            duration_ms=duration_ms,
            delay_ms=delay_ms,
            easing=easing
        )
        
        return await self.start_animation(f"fade_{target_id}_{time.time_ns()}", props)
    
    async def move(self, target_id: str, start_pos: Tuple[float, float], end_pos: Tuple[float, float],
                 duration_ms: int, delay_ms: int = 0, easing: EasingType = EasingType.EASE_OUT) -> str:
        """Create a move animation"""
        props = AnimationProps(
            target_id=target_id,
            property_name="position",
            start_value=start_pos,
            end_value=end_pos,
            duration_ms=duration_ms,
            delay_ms=delay_ms,
            easing=easing
        )
        
        return await self.start_animation(f"move_{target_id}_{time.time_ns()}", props)
    
    async def scale(self, target_id: str, start_scale: float, end_scale: float,
                  duration_ms: int, delay_ms: int = 0, easing: EasingType = EasingType.EASE_OUT) -> str:
        """Create a scale animation"""
        props = AnimationProps(
            target_id=target_id,
            property_name="scale",
            start_value=start_scale,
            end_value=end_scale,
            duration_ms=duration_ms,
            delay_ms=delay_ms,
            easing=easing
        )
        
        return await self.start_animation(f"scale_{target_id}_{time.time_ns()}", props)
    
    async def color(self, target_id: str, start_color: Tuple[float, float, float], 
                  end_color: Tuple[float, float, float], duration_ms: int, 
                  delay_ms: int = 0, easing: EasingType = EasingType.LINEAR) -> str:
        """Create a color animation"""
        props = AnimationProps(
            target_id=target_id,
            property_name="color",
            start_value=start_color,
            end_value=end_color,
            duration_ms=duration_ms,
            delay_ms=delay_ms,
            easing=easing
        )
        
        return await self.start_animation(f"color_{target_id}_{time.time_ns()}", props)
    
    async def sequence(self, animations: List[AnimationProps], gap_ms: int = 0) -> str:
        """Create a sequence of animations that play one after another"""
        group_name = f"sequence_{time.time_ns()}"
        group = self.create_animation_group(group_name)
        
        current_delay = 0
        
        for i, anim_props in enumerate(animations):
            # Add delay to each animation based on previous ones
            props = AnimationProps(
                target_id=anim_props.target_id,
                property_name=anim_props.property_name,
                start_value=anim_props.start_value,
                end_value=anim_props.end_value,
                duration_ms=anim_props.duration_ms,
                delay_ms=current_delay + anim_props.delay_ms,
                easing=anim_props.easing,
                loop=anim_props.loop,
                loop_count=anim_props.loop_count,
                on_complete=anim_props.on_complete
            )
            
            anim = Animation(props)
            group.add_animation(anim)
            
            # Next animation starts after this one plus gap
            current_delay += anim_props.duration_ms + anim_props.delay_ms + gap_ms
        
        # Start the group
        await self.start_animation_group(group_name)
        
        return group_name

# Singleton instance
_animation_manager = None

def get_animation_manager() -> AnimationManager:
    """Get or create the singleton animation manager instance"""
    global _animation_manager
    if _animation_manager is None:
        _animation_manager = AnimationManager()
    return _animation_manager

async def close_animation_manager():
    """Close the animation manager"""
    global _animation_manager
    if _animation_manager:
        await _animation_manager.stop()
        _animation_manager = None 