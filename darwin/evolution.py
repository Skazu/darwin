import random
import logging
from copy import deepcopy
from functools import wraps
from statistics import mean

from darwin.exceptions import MaxFitnessReached

logger = logging.getLogger(__name__)


def stop_on_fitness_wrapper(stop_on_fitness):
    """Decorate fitness function and raise MaxFitnessReached when
    `stop_on_fitness` was reached"""

    def decorator(fn):

        @wraps(fn)
        def fitness_wrapper(genome, *args, **kwargs):
            result = fn(genome, *args, **kwargs)

            if result >= stop_on_fitness:
                raise MaxFitnessReached(genome, stop_on_fitness)

            return result

        return fitness_wrapper

    return decorator


class Environment(object):

    def __init__(self, fitness_function, mutator, stop_on_fitness=None,
                 copy_fn=deepcopy):
        """
        :param fitness_function: callable taking a genome object and returning a
        float value indicating the individuals fitness (greater values mean
        fitter individuals)
        :param mutator: a mutator object
        :param copy_fn: a copy function for creating new objects
        """
        if stop_on_fitness:
            decorator = stop_on_fitness_wrapper(stop_on_fitness)
            fitness_function = decorator(fitness_function)

        self.fitness_function = fitness_function
        self.mutator = mutator
        self.copy_fn = copy_fn

    def remove_unfit(self, population, keep):
        """Return a new population containing the fittest `keep_ratio` of the given
        population.

        Even though the population is a new iterable, the individuals are the same
        objects as in `population`.
        """
        population = sorted(population, key=self.fitness_function, reverse=True)

        return population[:keep]

    def upsize_population(self, population, n=100):
        """Return a new population of size `n` based on the individuals in
        `population`.
        """
        pop_size = len(population)

        if pop_size >= n:
            return population

        return population + [self.copy_fn(x) for x in
                             random.choices(population, k=n-pop_size)]

    def mean_fitness(self, population):
        return mean(list(map(self.fitness_function, population)))

    def execute_callbacks(self, population, callbacks):
        if callbacks and callable(callbacks):
            callbacks(population)
        elif callbacks:
            for callback in callbacks:
                callback(population)

    def evolve(self, population, keep_ratio=.2, n_generations=1,
               population_size=100, generation_callback=None, copy=True):
        """

        :param population:
        :param keep_ratio:
        :param n_generations:
        :param population_size:
        :param generation_callback: a callback or a list of callbacks taking the
        population
        :param copy: ensure the given population is copied and not altered
        in-place
        :return:
        """
        if copy:
            population = [self.copy_fn(genome) for genome in population]

        population = self.upsize_population(population, population_size)
        self.execute_callbacks(population, generation_callback)

        msg = "Start: Mean fitness of top {:.2f} percent: {:f}"
        msg = msg.format(keep_ratio * 100, self.mean_fitness(population))
        logger.info(msg)

        for generation in range(n_generations):
            keep_n_fittest = int(keep_ratio * population_size) or 1
            population = self.remove_unfit(population, keep=keep_n_fittest)
            population = self.upsize_population(population, population_size)

            self.mutator(population)

            msg = "Gen #{:d}: Mean fitness of top {:.2f} %: {:f}"
            msg = msg.format(generation, keep_ratio * 100,
                             self.mean_fitness(population))
            logger.info(msg)

            self.execute_callbacks(population, generation_callback)

        return population
