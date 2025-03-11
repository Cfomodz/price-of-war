from math import log
from user_rep import UserStats
from settings import get_settings

class VoteCalculator:
    @staticmethod
    def calculate_weight(user: UserStats, vote_amount: int, current_price: int) -> float:
        settings = get_settings()
        
        # Base multipliers
        rep_mult = VoteCalculator._calculate_rep_multiplier(user)
        ext_mult = VoteCalculator._calculate_ext_multiplier(user)
        dist_mult = VoteCalculator._calculate_distance_multiplier(vote_amount, current_price)
        naughty_mult = settings.vote_weight_naughty_power ** sum(user.naughty_status.values())
        nice_mult = settings.vote_weight_nice_power ** sum(user.nice_status.values())
        
        return rep_mult * ext_mult * dist_mult * naughty_mult * nice_mult

    @staticmethod
    def _calculate_rep_multiplier(user: UserStats) -> float:
        settings = get_settings()
        lifetime_rep = settings.vote_weight_lifetime_base if user.lifetime_votes == 0 else 1.0 + log(user.lifetime_votes)
        show_rep = settings.vote_weight_show_base if user.show_votes == 0 else 2.0 + log(user.show_votes)
        return (lifetime_rep + show_rep * settings.vote_weight_show_multiplier) / 3

    @staticmethod
    def _calculate_distance_multiplier(vote_amount: int, current_price: int) -> float:
        settings = get_settings()
        
        if current_price == 0:
            return 0.0
            
        ratio = vote_amount / current_price
        if ratio < settings.vote_weight_ratio_min or ratio > settings.vote_weight_ratio_max:
            return 0.0
            
        if settings.vote_weight_ratio_sweet_min <= ratio <= settings.vote_weight_ratio_sweet_max:
            return abs(log(ratio)) * settings.vote_weight_sweet_multiplier
        else:
            return abs(log(ratio)) * settings.vote_weight_extreme_multiplier