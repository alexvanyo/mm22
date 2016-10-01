#!/usr/bin/python2
import socket
import json
import os
import random
import sys
from socket import error as SocketError
import errno
sys.path.append("../..")
import src.game.game_constants as game_consts
from src.game.character import *
from src.game.gamemap import *

# Game map that you can use to query 
gameMap = GameMap()

# --------------------------- SET THIS IS UP -------------------------
teamName = "Death Startup"
# ---------------------------------------------------------------------

# Set initial connection data
def initialResponse():
# ------------------------- CHANGE THESE VALUES -----------------------
    return {'TeamName': teamName,
            'Characters': [
                {"CharacterName": "JavaTheHutt",
                 "ClassId": "Archer"},
                {"CharacterName": "AdoB1KenoB",
                 "ClassId": "Archer"},
                {"CharacterName": "R=2,D=2",
                 "ClassId": "Archer"},
            ]}
# ---------------------------------------------------------------------

# Determine actions to take on a given turn, given the server response
def processTurn(serverResponse):
# --------------------------- CHANGE THIS SECTION -------------------------
    # Setup helper variables
    actions = []
    myteam = []
    enemyteam = []
    # Find each team and serialize the objects
    for team in serverResponse["Teams"]:
        if team["Id"] == serverResponse["PlayerInfo"]["TeamId"]:
            for characterJson in team["Characters"]:
                character = Character()
                character.serialize(characterJson)
                myteam.append(character)
        else:
            for characterJson in team["Characters"]:
                character = Character()
                character.serialize(characterJson)
                enemyteam.append(character)
# ------------------ You shouldn't change above but you can ---------------
    def get_lowest_health_character(characters):
        lowest_health = characters[0]
        for character in characters:
            if character.attributes.health < lowest_health.attributes.health:
                lowest_health = character

        return lowest_health

    one = None
    for character in myteam:
        if not character.is_dead():
            one = character
            break

    # Choose a target
    if one:
        targets = []
        for character in enemyteam:
            if not character.is_dead() and one.in_range_of(character, gameMap):
                targets.append(character)
                break

        if len(targets) > 0:
            lowest_health_enemy = get_lowest_health_character(targets)

            total_damage = 0
            total_debuff = 0

            for character in myteam:
                if not character.is_dead():
                    total_damage += character.attributes.damage - lowest_health_enemy.attributes.armor
                for abilityId, cooldown in character.abilities.items():
                    if abilityId == 2 and cooldown == 0:
                        total_debuff -= game_consts.abilitiesList[int(abilityId)]["StatChanges"][0]["Change"]
                        break

            for character in myteam:
                if total_damage < 4 * total_debuff or character.abilities.get(2) > 0:
                    actions.append({
                                "Action": "Attack",
                                "CharacterId": character.id,
                                "TargetId": lowest_health_enemy.id,
                            })
                else:
                    actions.append({
                                "Action": "Cast",
                                "CharacterId": character.id,
                                "TargetId": lowest_health_enemy.id,
                                "AbilityId": 2
                            })
        else:
            target = get_lowest_health_character(enemyteam)

            for character in myteam:
                actions.append({
                    "Action": "Move",
                    "CharacterId": character.id,
                    "TargetId": target.id,
                })
               

    # Send actions to the server
    return {
        'TeamName': teamName,
        'Actions': actions
    }
# ---------------------------------------------------------------------

# Main method
# @competitors DO NOT MODIFY
if __name__ == "__main__":
    # Config
    conn = ('localhost', 1337)
    if len(sys.argv) > 2:
        conn = (sys.argv[1], int(sys.argv[2]))

    # Handshake
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(conn)

    # Initial connection
    s.sendall(json.dumps(initialResponse()) + '\n')

    # Initialize test client
    game_running = True
    members = None

    # Run game
    try:
        data = s.recv(1024)
        while len(data) > 0 and game_running:
            value = None
            if "\n" in data:
                data = data.split('\n')
                if len(data) > 1 and data[1] != "":
                    data = data[1]
                    data += s.recv(1024)
                else:
                    value = json.loads(data[0])

                    # Check game status
                    if 'winner' in value:
                        game_running = False

                    # Send next turn (if appropriate)
                    else:
                        msg = processTurn(value) if "PlayerInfo" in value else initialResponse()
                        s.sendall(json.dumps(msg) + '\n')
                        data = s.recv(1024)
            else:
                data += s.recv(1024)
    except SocketError as e:
        if e.errno != errno.ECONNRESET:
            raise  # Not error we are looking for
        pass  # Handle error here.
    s.close()
