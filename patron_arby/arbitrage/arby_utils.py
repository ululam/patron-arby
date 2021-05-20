from typing import Tuple

from patron_arby.common.chain import AChainStep


class ArbyUtils:
    @staticmethod
    def calc_and_return_max_available_triangle_volume(step1: AChainStep, step2: AChainStep, step3: AChainStep) -> \
            Tuple[AChainStep, AChainStep, AChainStep]:
        """
        Given three steps, calculates the max available volume we can trade via the chain, and returns steps with
        adjusted volumes
        :return: Steps wth max available volume set
        """
        if step1.volume == 0 or step2.volume == 0 or step3.volume == 0:
            return ArbyUtils._return_all_zeros(step1, step2, step3)

        # How many coins A we have at market1?
        coinA_volume_market1 = ArbyUtils._get_what_we_propose_volume(step1)
        # That corresponds to the following number of coins B
        coinB_volume_market1 = ArbyUtils._get_what_we_get_volume(step1)

        # Market 2: Convert volume to coinA
        coinB_volume_market2 = ArbyUtils._get_what_we_propose_volume(step2)
        coinC_volume_market2 = ArbyUtils._get_what_we_get_volume(step2)
        coinA_volume_market2 = coinB_volume_market2 * (coinA_volume_market1 / coinB_volume_market1)

        # Market 3: Convert volume to coinA
        coinC_volume_market3 = ArbyUtils._get_what_we_propose_volume(step3)
        coinB_volume_market3 = coinC_volume_market3 * (coinB_volume_market2 / coinC_volume_market2)
        coinA_volume_market3 = coinB_volume_market3 * (coinA_volume_market1 / coinB_volume_market1)

        # Max volume we can trade is the min out of 3 markets
        coinA_max_available = min(coinA_volume_market1, coinA_volume_market2, coinA_volume_market3)

        # Now, adjust all the steps volumes
        step1 = ArbyUtils._adjust_step_volume(step1, coinA_max_available)

        coinB_after_step1 = ArbyUtils._get_what_we_get_volume(step1)
        step2 = ArbyUtils._adjust_step_volume(step2, coinB_after_step1)

        coinC_after_step2 = ArbyUtils._get_what_we_get_volume(step2)
        step3 = ArbyUtils._adjust_step_volume(step3, coinC_after_step2)

        return step1, step2, step3

    @staticmethod
    def _adjust_step_volume(step: AChainStep, prev_step_coin_volume: float):
        step2_volume = prev_step_coin_volume / step.price if step.is_buy() else prev_step_coin_volume
        return step.clone_with_volume(step2_volume)

    @staticmethod
    def _return_all_zeros(step1: AChainStep, step2: AChainStep, step3: AChainStep) -> \
            Tuple[AChainStep, AChainStep, AChainStep]:
        return step1.clone_with_volume(0), step2.clone_with_volume(0), step3.clone_with_volume(0)

    @staticmethod
    def _get_what_we_propose_volume(step: AChainStep) -> float:
        return step.volume * step.price if step.is_buy() else step.volume

    @staticmethod
    def _get_what_we_get_volume(step: AChainStep) -> float:
        return step.volume if step.is_buy() else step.volume * step.price
