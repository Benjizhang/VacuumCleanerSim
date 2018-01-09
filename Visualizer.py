import os
from time import strftime, gmtime

import pygame
from pygame.locals import *

from events.EventType import EventType
from events.ObstacleDrawn import ObstacleDrawn
from events.RobotDrawn import RobotDrawn
from utils.Runmode import Runmode
from utils.colorUtils import *
from utils.confUtils import LOG as log
from utils.confUtils import CONF as conf


class Visualizer:
    def __init__(self, env, clock):
        pygame.init()
        w, h, _ = env.get_params()

        self.ticks = 0
        self.clock = clock
        self.run_mode = Runmode.BUILD

        flags = DOUBLEBUF
        # flags = FULLSCREEN | DOUBLEBUF
        self.screen = pygame.display.set_mode((w, h), flags)
        self.screen.set_alpha(None)

        self.font = pygame.font.Font(None, 20)

        self.tile_group = pygame.sprite.Group()

        self.wall_group = pygame.sprite.Group()
        self.wall_group.add(env.walls)

        self.obstacle_group = pygame.sprite.Group()
        self.obstacle_group.add(env.obstacles)

        self.robot = env.robot
        self.robot_group = pygame.sprite.Group()
        if self.robot is not None:
            self.robot_group.add(self.robot)

        # --- used for statistic --
        self.tile_count = 0
        self.covered_tiles = 0

        # --- Temp rectangle for placing new rectangles ---
        self.mouse_down = False
        self.start_point = None
        self.temp_rectangle = None
        self.new_rectangle = None

        # --- Temp robot tuple ---
        self.temp_robot = None

        # --- display configuration ---
        self.show_coverage_path = True

        self.time = strftime("%Y%m%d%H%M%S", gmtime())

    def update(self, sim_events=None, pygame_events=None):
        if sim_events is not None and len(sim_events) != 0:
            self.handle_sim_events(sim_events)
        if pygame_events is not None:
            self.handle_pygame_events(pygame_events)

        if self.run_mode == Runmode.SIM:
            if self.ticks % 1000 == 0:
                self.save_screenshot()

            self.ticks = self.ticks + 1

        self.draw()

    def handle_pygame_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r and self.robot is None:
                    x, y = pygame.mouse.get_pos()
                    radius = conf["robot"]["radius"]
                    self.temp_robot = (x, y, radius)
                if event.key == pygame.K_p:
                    self.show_coverage_path = not self.show_coverage_path
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.mouse_down = True
                self.start_point = pygame.mouse.get_pos()
            if event.type == pygame.MOUSEBUTTONUP:
                self.mouse_down = False
                self.new_rectangle = self.temp_rectangle
                self.start_point = None
                self.temp_rectangle = None

    def handle_sim_events(self, events):
        for event in events:
            if event.type == EventType.OBSTACLE_ADDED:
                log.info("Add Obstacle " + str(event.new_obstacle))
                self.obstacle_group.add(event.new_obstacle)
            if event.type == EventType.ROBOT_PLACED:
                log.info("Robot placed " + str(event.placed_robot))
                self.robot_group.add(event.placed_robot)
            if event.type == EventType.TILE_COVERED:
                self.covered_tiles = self.covered_tiles + 1
                self.tile_group.add(event.tile)

    def get_draw_events(self):
        events = []

        if self.new_rectangle is not None:
            ret = self.new_rectangle
            self.new_rectangle = None
            events.append(ObstacleDrawn(ret))

        if self.temp_robot is not None:
            events.append(RobotDrawn(self.temp_robot))
            self.temp_robot = None

        return events

    def draw_temp_rectangle(self):
        if self.mouse_down:
            x, y = pygame.mouse.get_pos()
            self.temp_rectangle = [self.start_point[0], self.start_point[1], x - self.start_point[0],
                                   y - self.start_point[1]]

            pygame.draw.rect(self.screen, RED, self.temp_rectangle)

    def clean_obstacles(self):
        self.obstacle_group.empty()

    def set_run_mode(self, new_run_mode):
        self.run_mode = new_run_mode

    def set_tile_count(self, count: int):
        self.tile_count = count

    def draw_fps(self):
        if conf["debug"]["draw_fps"]:
            fps = self.font.render("FPS: " + str(int(self.clock.get_fps())), True, RED)
            self.screen.blit(fps, (20, 20))

    def draw_coverage(self):
        if conf["debug"]["draw_coverage"]:
            percentage = self.covered_tiles / self.tile_count * 100 if self.tile_count > 0 else 0
            coverage_text = self.font.render("Coverage: " + str(int(percentage)) + "%", True, RED)
            self.screen.blit(coverage_text, (20, 40))

    def draw_time(self):
        if conf["debug"]["draw_time"] and self.run_mode == Runmode.SIM:
            time = self.font.render("Time: " + str(self.ticks), True, RED)
            self.screen.blit(time, (20, 60))

    def draw(self):
        self.screen.fill(WHITE)

        self.tile_group.update()
        self.wall_group.update()
        self.obstacle_group.update()
        self.robot_group.update()

        if self.show_coverage_path:
            self.tile_group.draw(self.screen)
        self.wall_group.draw(self.screen)
        self.obstacle_group.draw(self.screen)
        self.robot_group.draw(self.screen)

        self.draw_temp_rectangle()
        self.draw_fps()
        self.draw_time()
        self.draw_coverage()

        pygame.display.flip()

    def save_screenshot(self):
        log.info("make screenshot")
        if not os.path.exists("output"):
            os.makedirs("output")

        if not os.path.exists("output/" + str(self.time)):
            os.makedirs("output/" + str(self.time))

        filename = "output/" + str(self.time) + "/" + str(self.ticks) + ".png"
        pygame.image.save(self.screen, filename)
