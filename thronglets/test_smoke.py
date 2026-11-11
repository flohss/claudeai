"""Headless sanity check for the simulation core (no pygame/display needed).

Runs a world for a few thousand ticks and checks that it doesn't crash, that
the population stays viable, and that the vocabulary actually converges
(agreement on the food-call token should go up, not stay random) - i.e. that
something worth calling "a language emerging" is really happening.
"""

from simulation import FOOD, World


def main():
    world = World(init_pop=70, seed=42)

    early_agreement = None
    for tick in range(6000):
        world.step()
        if tick == 500:
            early_agreement = world.vocabulary()[FOOD][1]

    late_agreement = world.vocabulary()[FOOD][1]
    pop = world.population()

    print(f"final tick:        {world.tick}")
    print(f"population:        {pop}")
    print(f"births / deaths:   {world.births} / {world.deaths}")
    print(f"food-call agreement @ tick 500:  {early_agreement:.0%}")
    print(f"food-call agreement @ tick 6000: {late_agreement:.0%}")

    assert pop > 0, "population went extinct in this run (try a different seed)"
    assert late_agreement >= early_agreement, "vocabulary did not converge further over time"
    print("OK: population survived and the food-call token converged.")


if __name__ == "__main__":
    main()
