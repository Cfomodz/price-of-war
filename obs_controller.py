import asyncio
import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
from animation_manager import get_animation_manager, AnimationProps, EasingType
from user_rep import UserStats
from settings import get_settings

logger = logging.getLogger("obs_controller")

class OBSEffect:
    """Class representing an active visual effect in OBS"""
    def __init__(self, user_id: str, effect_type: str, intensity: float, duration_ms: int):
        self.user_id = user_id
        self.effect_type = effect_type
        self.intensity = intensity
        self.duration_ms = duration_ms
        self.start_time = datetime.now()
        self.animation_ids: List[str] = []
        
    def is_expired(self) -> bool:
        """Check if the effect has expired"""
        elapsed_ms = (datetime.now() - self.start_time).total_seconds() * 1000
        return elapsed_ms > self.duration_ms

class OBSController:
    def __init__(self):
        self.current_effects: Dict[str, OBSEffect] = {}
        self.logger = logger
        self.animation_manager = None  # Will be initialized on first use
        self.connected = False
        self.settings = get_settings()
        
        # Element IDs in OBS
        self.ui_elements = {
            "up_arrow": "up_arrow_element",
            "down_arrow": "down_arrow_element",
            "set_indicator": "set_indicator_element",
            "price_display": "price_display_element",
            "nice_glow": "nice_glow_element",
            "naughty_glow": "naughty_glow_element",
            "user_display": "user_display_element"
        }
        
        # Effect durations from settings
        self.effect_durations = {
            "up": self.settings.obs_effect_duration_up,
            "down": self.settings.obs_effect_duration_down,
            "set": self.settings.obs_effect_duration_set,
            "nice_glow": self.settings.obs_effect_duration_nice_glow,
            "naughty_glow": self.settings.obs_effect_duration_naughty_glow,
            "user_display": self.settings.obs_effect_duration_user_display
        }
    
    async def initialize(self):
        """Initialize the OBS controller and animation manager"""
        if self.animation_manager is None:
            self.animation_manager = get_animation_manager()
            await self.animation_manager.start()
            
            # Register callbacks for animation updates
            self._register_animation_callbacks()
            
            self.logger.info("OBS controller initialized with animation manager")
            
        # TODO: Connect to OBS WebSocket (if needed)
        self.connected = True
    
    def _register_animation_callbacks(self):
        """Register callbacks for all animatable properties"""
        # Register opacity callbacks
        for element_id in self.ui_elements.values():
            self.animation_manager.register_animation_callback(
                element_id, "opacity", self._handle_opacity_animation
            )
            self.animation_manager.register_animation_callback(
                element_id, "scale", self._handle_scale_animation
            )
            self.animation_manager.register_animation_callback(
                element_id, "position", self._handle_position_animation
            )
            self.animation_manager.register_animation_callback(
                element_id, "color", self._handle_color_animation
            )
    
    async def _handle_opacity_animation(self, target_id: str, property_name: str, value: float):
        """Handle opacity animation updates"""
        if not self.connected:
            return
            
        # In a real implementation, this would send commands to OBS WebSocket
        # For now, just log it
        self.logger.debug(f"OBS Animation: {target_id} {property_name} = {value}")
        
        # TODO: Add actual OBS WebSocket integration code here
        # Example: await self.obs_ws.set_source_property(target_id, "opacity", value)
    
    async def _handle_scale_animation(self, target_id: str, property_name: str, value: float):
        """Handle scale animation updates"""
        if not self.connected:
            return
            
        self.logger.debug(f"OBS Animation: {target_id} {property_name} = {value}")
        # TODO: Add actual OBS implementation
    
    async def _handle_position_animation(self, target_id: str, property_name: str, value: Tuple[float, float]):
        """Handle position animation updates"""
        if not self.connected:
            return
            
        x, y = value
        self.logger.debug(f"OBS Animation: {target_id} {property_name} = ({x}, {y})")
        # TODO: Add actual OBS implementation
    
    async def _handle_color_animation(self, target_id: str, property_name: str, value: Tuple[float, float, float]):
        """Handle color animation updates"""
        if not self.connected:
            return
            
        r, g, b = value
        self.logger.debug(f"OBS Animation: {target_id} {property_name} = ({r}, {g}, {b})")
        # TODO: Add actual OBS implementation
    
    async def apply_effect(self, user: UserStats, vote_effect: dict):
        """Apply a visual effect based on a user's vote"""
        if self.animation_manager is None:
            await self.initialize()
        
        direction = vote_effect.get('direction', 'up')
        intensity = vote_effect.get('intensity', 1.0)
        
        # Create effect tracking object
        effect_id = f"{user.user_id}_{direction}_{datetime.now().timestamp()}"
        effect_duration = self.effect_durations.get(direction, 2000)
        effect = OBSEffect(user.user_id, direction, intensity, effect_duration)
        self.current_effects[effect_id] = effect
        
        # Calculate naughty/nice levels for UI effects
        naughty_level = self._calculate_naughty_level(user)
        nice_level = self._calculate_nice_level(user)
        
        # Log effect
        self.logger.info(f"Applying OBS effect: user={user.user_id}, direction={direction}, "
                       f"intensity={intensity}, naughty={naughty_level}, nice={nice_level}")
        
        # Create animation sequence based on vote direction
        if direction == "up":
            await self._create_up_animation(effect_id, effect, intensity, nice_level)
        elif direction == "down":
            await self._create_down_animation(effect_id, effect, intensity, naughty_level)
        elif direction == "set":
            await self._create_set_animation(effect_id, effect, intensity)
        
        # Show user display with animation
        user_display_id = await self._show_user_display(user, intensity, effect_duration)
        effect.animation_ids.append(user_display_id)
        
        # Schedule cleanup after effect duration
        asyncio.create_task(self._cleanup_effect(effect_id, effect_duration))
    
    async def _create_up_animation(self, effect_id: str, effect: OBSEffect, intensity: float, nice_level: float):
        """Create animations for 'up' vote effect"""
        arrow_element = self.ui_elements["up_arrow"]
        animation_manager = self.animation_manager
        
        # Create arrow animation
        # 1. Fade in
        fade_in_id = await animation_manager.fade(
            target_id=arrow_element,
            start_opacity=0.0,
            end_opacity=1.0,
            duration_ms=200,
            easing=EasingType.EASE_OUT
        )
        effect.animation_ids.append(fade_in_id)
        
        # 2. Scale up based on intensity
        scale_up_id = await animation_manager.scale(
            target_id=arrow_element,
            start_scale=1.0,
            end_scale=1.0 + (intensity * 0.5),  # Scale up to 1.5x for max intensity
            duration_ms=300,
            delay_ms=200,
            easing=EasingType.BOUNCE
        )
        effect.animation_ids.append(scale_up_id)
        
        # 3. Fade out
        fade_out_id = await animation_manager.fade(
            target_id=arrow_element,
            start_opacity=1.0,
            end_opacity=0.0,
            duration_ms=300,
            delay_ms=800,
            easing=EasingType.EASE_IN
        )
        effect.animation_ids.append(fade_out_id)
        
        # If user is 'nice', show nice glow effect
        if nice_level > 0.5:
            nice_element = self.ui_elements["nice_glow"]
            nice_glow_id = await animation_manager.fade(
                target_id=nice_element,
                start_opacity=0.0,
                end_opacity=nice_level,  # Opacity based on nice level
                duration_ms=500,
                delay_ms=200,
                easing=EasingType.EASE_IN_OUT
            )
            effect.animation_ids.append(nice_glow_id)
            
            # Fade out nice glow
            nice_fade_out_id = await animation_manager.fade(
                target_id=nice_element,
                start_opacity=nice_level,
                end_opacity=0.0,
                duration_ms=500,
                delay_ms=800,
                easing=EasingType.EASE_IN
            )
            effect.animation_ids.append(nice_fade_out_id)
    
    async def _create_down_animation(self, effect_id: str, effect: OBSEffect, intensity: float, naughty_level: float):
        """Create animations for 'down' vote effect"""
        arrow_element = self.ui_elements["down_arrow"]
        animation_manager = self.animation_manager
        
        # Create arrow animation similar to up but with down arrow
        # 1. Fade in
        fade_in_id = await animation_manager.fade(
            target_id=arrow_element,
            start_opacity=0.0,
            end_opacity=1.0,
            duration_ms=200,
            easing=EasingType.EASE_OUT
        )
        effect.animation_ids.append(fade_in_id)
        
        # 2. Scale up based on intensity
        scale_up_id = await animation_manager.scale(
            target_id=arrow_element,
            start_scale=1.0,
            end_scale=1.0 + (intensity * 0.5),
            duration_ms=300,
            delay_ms=200,
            easing=EasingType.BOUNCE
        )
        effect.animation_ids.append(scale_up_id)
        
        # 3. Fade out
        fade_out_id = await animation_manager.fade(
            target_id=arrow_element,
            start_opacity=1.0,
            end_opacity=0.0,
            duration_ms=300,
            delay_ms=800,
            easing=EasingType.EASE_IN
        )
        effect.animation_ids.append(fade_out_id)
        
        # If user is 'naughty', show naughty glow effect
        if naughty_level > 0.5:
            naughty_element = self.ui_elements["naughty_glow"]
            naughty_glow_id = await animation_manager.fade(
                target_id=naughty_element,
                start_opacity=0.0,
                end_opacity=naughty_level,  # Opacity based on naughty level
                duration_ms=500,
                delay_ms=200,
                easing=EasingType.EASE_IN_OUT
            )
            effect.animation_ids.append(naughty_glow_id)
            
            # Fade out naughty glow
            naughty_fade_out_id = await animation_manager.fade(
                target_id=naughty_element,
                start_opacity=naughty_level,
                end_opacity=0.0,
                duration_ms=500,
                delay_ms=800,
                easing=EasingType.EASE_IN
            )
            effect.animation_ids.append(naughty_fade_out_id)
    
    async def _create_set_animation(self, effect_id: str, effect: OBSEffect, intensity: float):
        """Create animations for 'set' vote effect"""
        set_element = self.ui_elements["set_indicator"]
        animation_manager = self.animation_manager
        settings = self.settings
        
        # Create 'set' animation sequence
        # 1. Fade in
        fade_in_id = await animation_manager.fade(
            target_id=set_element,
            start_opacity=0.0,
            end_opacity=1.0,
            duration_ms=settings.animation_fade_in_duration,
            easing=EasingType.EASE_OUT
        )
        effect.animation_ids.append(fade_in_id)
        
        # 2. Pulse with color change
        color_start = self._parse_color(settings.animation_set_color_start)
        color_end = self._parse_color(settings.animation_set_color_end)
        
        color_id = await animation_manager.color(
            target_id=set_element,
            start_color=color_start,
            end_color=color_end,
            duration_ms=settings.animation_color_duration,
            easing=EasingType.EASE_IN_OUT
        )
        effect.animation_ids.append(color_id)
        
        # 3. Fade out
        fade_out_id = await animation_manager.fade(
            target_id=set_element,
            start_opacity=1.0,
            end_opacity=0.0,
            duration_ms=settings.animation_fade_out_duration,
            delay_ms=settings.animation_color_duration + 200,
            easing=EasingType.EASE_IN
        )
        effect.animation_ids.append(fade_out_id)
    
    async def _show_user_display(self, user: UserStats, intensity: float, duration_ms: int) -> str:
        """Show the user display with animations"""
        element_id = self.ui_elements["user_display"]
        
        # Set initial text and fade in
        await self.animation_manager.set_text(element_id, user.display_name)
        await self._fade_in(element_id)
        
        # Schedule fade out near the end
        asyncio.create_task(
            self._delayed_fade_out(
                element_id,
                delay_ms=duration_ms - self.settings.animation_user_display_fade
            )
        )
        
        return element_id
    
    async def _cleanup_effect(self, effect_id: str, delay_ms: int):
        """Clean up effect after it expires"""
        await asyncio.sleep(delay_ms / 1000)
        
        if effect_id in self.current_effects:
            effect = self.current_effects[effect_id]
            
            # Cancel any ongoing animations if needed
            if self.animation_manager:
                for anim_id in effect.animation_ids:
                    await self.animation_manager.cancel_animation(anim_id)
            
            # Remove from active effects
            del self.current_effects[effect_id]
            self.logger.debug(f"Cleaned up effect {effect_id}")
    
    def _calculate_naughty_level(self, user: UserStats) -> float:
        """Calculate how 'naughty' a user is (0.0 to 1.0)"""
        lifetime_naughty = 1 if user.naughty_status.get('lifetime', False) else 0
        show_naughty = 1 if user.naughty_status.get('show', False) else 0
        
        # Use settings for factor weights
        base_level = (
            lifetime_naughty * self.settings.obs_naughty_lifetime_factor + 
            show_naughty * self.settings.obs_naughty_show_factor
        )
        
        # Add some contribution from erroneous votes using configured factor
        if user.lifetime_votes > 0:
            error_ratio = min(1.0, user.erroneous_votes / max(1, user.lifetime_votes))
            error_contribution = error_ratio * self.settings.obs_naughty_errors_contribution
            
            return min(1.0, base_level + error_contribution)
        
        return base_level

    def _calculate_nice_level(self, user: UserStats) -> float:
        """Calculate how 'nice' a user is (0.0 to 1.0)"""
        lifetime_nice = 1 if user.nice_status.get('lifetime', False) else 0
        show_nice = 1 if user.nice_status.get('show', False) else 0
        
        # Use settings for factor weights
        base_level = (
            lifetime_nice * self.settings.obs_nice_lifetime_factor + 
            show_nice * self.settings.obs_nice_show_factor
        )
        
        # Add contribution from vote count using configured factors
        vote_contribution = min(
            self.settings.obs_nice_votes_contribution,
            (user.lifetime_votes / self.settings.obs_nice_votes_threshold) * 
            self.settings.obs_nice_votes_contribution
        )
        
        return min(1.0, base_level + vote_contribution)
    
    async def close(self):
        """Close the OBS controller and animation manager"""
        if self.animation_manager:
            await self.animation_manager.stop()
            
        # TODO: Close OBS WebSocket connection if open
        self.connected = False
        self.logger.info("OBS controller closed")

    async def _fade_in(self, element_id: str) -> str:
        """Fade in an element"""
        return await self.animation_manager.animate_opacity(
            element_id,
            start=0.0,
            end=1.0,
            duration_ms=self.settings.animation_fade_in_duration,
            easing=EasingType.EASE_OUT
        )

    async def _fade_out(self, element_id: str) -> str:
        """Fade out an element"""
        return await self.animation_manager.animate_opacity(
            element_id,
            start=1.0,
            end=0.0,
            duration_ms=self.settings.animation_fade_out_duration,
            easing=EasingType.EASE_IN
        )

    async def _scale_up(self, element_id: str) -> str:
        """Scale up an element"""
        settings = self.settings
        return await self.animation_manager.animate_scale(
            element_id,
            start=(settings.animation_scale_min, settings.animation_scale_min),
            end=(settings.animation_scale_max, settings.animation_scale_max),
            duration_ms=settings.animation_scale_duration,
            easing=EasingType.EASE_OUT
        )

    async def _scale_down(self, element_id: str) -> str:
        """Scale down an element"""
        settings = self.settings
        return await self.animation_manager.animate_scale(
            element_id,
            start=(settings.animation_scale_max, settings.animation_scale_max),
            end=(settings.animation_scale_min, settings.animation_scale_min),
            duration_ms=settings.animation_scale_duration,
            easing=EasingType.EASE_IN
        )

    async def _move_up(self, element_id: str) -> str:
        """Move an element up"""
        settings = self.settings
        return await self.animation_manager.animate_position(
            element_id,
            start=(0, 0),
            end=(0, -settings.animation_move_distance),
            duration_ms=settings.animation_move_duration,
            easing=EasingType.EASE_OUT
        )

    async def _move_down(self, element_id: str) -> str:
        """Move an element down"""
        settings = self.settings
        return await self.animation_manager.animate_position(
            element_id,
            start=(0, -settings.animation_move_distance),
            end=(0, 0),
            duration_ms=settings.animation_move_duration,
            easing=EasingType.EASE_IN
        )

    async def _color_shift(self, element_id: str, start_color: str, end_color: str) -> str:
        """Shift the color of an element"""
        return await self.animation_manager.animate_color(
            element_id,
            start=start_color,
            end=end_color,
            duration_ms=self.settings.animation_color_duration,
            easing=EasingType.LINEAR
        )

    def _parse_color(self, color_str: str) -> Tuple[float, float, float]:
        """Parse a comma-separated color string into RGB tuple"""
        try:
            r, g, b = map(float, color_str.split(','))
            return (r, g, b)
        except (ValueError, TypeError):
            self.logger.warning(f"Invalid color string format: {color_str}, using default")
            return (1.0, 1.0, 1.0)

    async def _delayed_fade_out(self, element_id: str, delay_ms: int):
        """Delayed fade out of an element"""
        await asyncio.sleep(delay_ms / 1000)
        await self._fade_out(element_id)