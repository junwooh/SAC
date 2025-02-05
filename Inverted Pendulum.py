import gym
from SAC import SAC_agent
import numpy as np
from matplotlib import pyplot as plt
import datetime
import tensorflow as tf
import sys

sys.path.append('C:\\Users\\junwo\\.mujoco\\mujoco200\\bin;%PATH%')

env = gym.make('InvertedPendulum-v2')
env.reset()

state_dim = env.observation_space.shape[0]
action_dim = env.action_space.shape[0]

action_max = env.action_space.high[0]

# Episode parmeters
N_EPISODES = 250
RANDOM = 10

N_EPISODES_PLAY = 100

# SAC parmeters
LEARNING_RATE = 0.0005
GAMMA = 0.99
TAU = 0.01
LOG_STD_MIN = -20
LOG_STD_MAX = 2

TARGET_UPDATE_EVERY = 1
MAX_MEMORY = 10_000
START_TRAINING = 1_000
BATCH_SIZE = 128

MODEL_NAME = "trial_invertedPendulum"

current_time = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
train_log_dir = 'path/logs/mujoco_' + current_time
play_log_dir = 'path/logs/mujoco_' + current_time + '_playback'

def main():
    summary_writer = tf.summary.create_file_writer(train_log_dir)

    agent = SAC_agent(state_dim, action_dim, action_max,
                      LEARNING_RATE, TAU, GAMMA,
                      TARGET_UPDATE_EVERY, MAX_MEMORY, BATCH_SIZE, 
                      LOG_STD_MIN, LOG_STD_MAX)
    
    epoch = 0
    summary = {}

    for episode in range(N_EPISODES):

        state, reward_episode, done, step = env.reset(), 0, False, 0
        
        while not done:
            env.render()
            
            if len(agent.memory) < START_TRAINING:
                action = agent.actor.act(state, use_random=True)
            else:
                action = agent.actor.act(state, use_random=False)
                
            next_state, reward, done, _ = env.step(action)

            reward = -1 if (done and step<999) else reward
           
            agent.remember(state, action, reward, next_state, done)

            reward_episode += reward

            state = next_state
            step += 1
        
        print("========= EPISODE: {} =========".format(episode+1))
        print("Total Reward:", reward_episode)

        if len(agent.memory) > START_TRAINING:
            loss_critic, loss_actor = [], []
            for _ in range(200):
                summary = agent.train()
                actor_loss = summary['actor_loss']
                critic_loss = np.mean([summary['Q1_loss'],summary['Q2_loss']])

                with summary_writer.as_default():
                    tf.summary.scalar('Loss/actor_loss', summary['actor_loss'], step=epoch)
                    tf.summary.scalar('Loss/q1_loss', summary['Q1_loss'], step=epoch)
                    tf.summary.scalar('Loss/q2_loss', summary['Q2_loss'], step=epoch)
                    tf.summary.scalar('Loss/alpha_loss', summary['alpha_loss'], step=epoch)

                    tf.summary.scalar('Stats/alpha', summary['alpha'], step=epoch)
                    tf.summary.scalar('Stats/log_alpha', summary['log_alpha'], step=epoch)
                summary_writer.flush()
                
                loss_critic.append(critic_loss)
                loss_actor.append(actor_loss)

                epoch += 1
            mean_loss_critic = np.mean(loss_critic)
            mean_loss_actor = np.mean(loss_actor)
            print("Critic Mean Loss: {}, Actor Mean Loss: {}, Alpha: {}".format(mean_loss_critic, mean_loss_actor, agent.alpha.value()))

        with summary_writer.as_default():
            tf.summary.scalar('Main/episode_reward', reward_episode, step=episode)
        summary_writer.flush()

    agent.actor.save(MODEL_NAME)
    env.close()

    return 

def play_back():
    summary_writer = tf.summary.create_file_writer(play_log_dir)
    
    agent = SAC_agent(state_dim, action_dim, action_max)
    agent.actor.load(MODEL_NAME)

    for episode in range(N_EPISODES_PLAY):
        state, reward_episode, done = env.reset(), 0, False

        while not done:
            env.render()
            action = agent.actor.act(state, test=True, use_random=False)

            next_state, reward, done, _ = env.step(action)

            reward_episode += reward

            state = next_state

        print("========= EPISODE: {} =========".format(episode+1))
        print("Total Reward:", reward_episode)
        
        with summary_writer.as_default():
            tf.summary.scalar('Main/episode_reward', reward_episode, step=episode)
        summary_writer.flush()
    env.close()
    
    return 

if __name__ == "__main__":
    main()
    # play_back()