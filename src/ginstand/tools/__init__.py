"""Checks this package runs against itself, and CI runs against every commit.

Each tool is a module with a ``main`` that returns an exit status and prints its
findings. They are not tests. A test says a behaviour is right; these say the
codebase still has a property that nothing else would notice losing: that every
public thing is documented, that no module reads the clock, that the layers
still point one way.

The rule for adding one: a check earns its place if it has already caught
something. A check that has never fired is an opinion with a build step.
"""
