from datetime import datetime
from decimal import Decimal

from base import clear_database, clear_session
from core import create_user, select_all_users, create_party, select_all_parties, add_user_to_queue
from party import UserParty
from user import UserQueue

from sqlalchemy import select

import warnings

warnings.filterwarnings('ignore')

# for user creation
user_id_list = ['alexnikko', 'log_loss', 'random_cool_user']
username_list = ['Alex', 'Darkhan', 'Cool Name']
is_organizer_list = [True, False, True]

# for party creation
title_list = ['Sueta main', 'Sueta natural']
description_list = ['Doing TG bot for Sueta group', 'DEBUGGING SUETA BOT']
location_list = ['TELEGRAM CALL', 'import ipdb; ipdb.set_trace()']
date_list = ['14-12-2021', '15-12-2021']
organizer_id_list = ['alexnikko', 'log_loss']
cost_list = ['100.5', '999.99']
done_list = [False, False]

if __name__ == '__main__':
    # clear_database()
    session = clear_session()

    # create users
    for user_id, username, is_organizer in zip(user_id_list, username_list, is_organizer_list):
        create_user(user_id, username, is_organizer, session=session)
    # print users
    users = select_all_users(session=session)
    users = list(users)
    print('User list:')
    for user in users:
        print(user)

    # create parties
    for title, description, location, date, organizer_id, cost, done in zip(
            title_list, description_list, location_list, date_list, organizer_id_list, cost_list, done_list
    ):
        date = datetime.strptime(date, '%d-%M-%Y')
        cost = Decimal(cost)
        create_party(title, description, location, date, organizer_id, cost, done, session=session)
    # print parties
    parties = select_all_parties(session=session)
    parties = list(parties)
    print('Party list:')
    for party in parties:
        print(party)
    #  append users to party
    parties[0].users.append(users[1])

    parties[1].users.append(users[0])
    parties[1].users.append(users[2])

    # commit, so changes are written to DB in table party_participants
    session.commit()
    print('Party participants')
    for party in parties:
        print(party.users)

    print('party_participations DATABASE CONTENT:')
    for x in list(session.execute(select(UserParty)).all()):
        print(x)

    # adding users to queue of parties creation
    add_user_to_queue('log_loss', has_plan=False, session=session)
    add_user_to_queue('alexnikko', has_plan=False, session=session)

    # print current queue
    print('CURRENT QUEUE STATE:')
    for user in session.execute(select(UserQueue)).scalars():
        print(user)
    session.close()
