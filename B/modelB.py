import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import sklearn
import os
import torch
import cv2
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics import confusion_matrix
import seaborn as sns
from sklearn.svm import SVC
from sklearn.utils import shuffle
from sklearn.metrics import classification_report,accuracy_score
from torch.optim import lr_scheduler
import copy
from sklearn.decomposition import PCA
import joblib

save_image = False

class CNN(nn.Module):
    def __init__(self):
        super(CNN, self).__init__()
        self.conv1 = nn.Conv2d(in_channels=3, out_channels=16, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(in_channels=16, out_channels=64, kernel_size=3, padding=1)
        self.pool1 = nn.MaxPool2d(kernel_size=2, stride=2)
        self.pool2 = nn.MaxPool2d(kernel_size=2, stride=2)
        self.fc1 = nn.Linear(64 * 7 * 7, 128)
        self.fc2 = nn.Linear(128, 9)
        
    def forward(self, x):
        x = self.pool1(torch.relu(self.conv1(x)))
        x = self.pool2(torch.relu(self.conv2(x)))
        x = x.reshape(-1, 64 * 7 * 7)
        x = torch.relu(self.fc1(x))
        x = self.fc2(x)
        # x = torch.softmax(x, dim=1)
        return x
    
class CNN2(nn.Module):
    def __init__(self):
        super(CNN2, self).__init__()
        self.conv1 = nn.Conv2d(in_channels=3, out_channels=16, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(in_channels=16, out_channels=32, kernel_size=3, padding=1)
        self.conv3 = nn.Conv2d(in_channels=32, out_channels=64, kernel_size=3, padding=1)
        self.pool1 = nn.MaxPool2d(kernel_size=2, stride=2)
        self.pool2 = nn.MaxPool2d(kernel_size=2, stride=2)
        # self.pool2 = nn.MaxPool2d(kernel_size=2, stride=2)
        self.fc1 = nn.Linear(64 * 7 * 7, 128)
        self.fc2 = nn.Linear(128, 9)
        
    def forward(self, x):
        x = self.pool1(torch.relu(self.conv1(x)))
        x = self.pool2(torch.relu(self.conv2(x)))
        x = torch.relu(self.conv3(x))
        x = x.reshape(-1, 64 * 7 * 7)
        x = torch.relu(self.fc1(x))
        x = self.fc2(x)
        return x
    
class CNN3(nn.Module):
    def __init__(self):
        super(CNN3, self).__init__()
        self.conv1 = nn.Conv2d(in_channels=3, out_channels=16, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(in_channels=16, out_channels=32, kernel_size=3, padding=1)
        self.conv3 = nn.Conv2d(in_channels=32, out_channels=64, kernel_size=3, padding=1)
        self.conv4 = nn.Conv2d(in_channels=64, out_channels=64, kernel_size=3, padding=1)
        self.pool1 = nn.MaxPool2d(kernel_size=2, stride=2)
        self.pool2 = nn.MaxPool2d(kernel_size=2, stride=2)
        # self.pool2 = nn.MaxPool2d(kernel_size=2, stride=2)
        self.fc1 = nn.Linear(64 * 7 * 7, 128)
        self.fc2 = nn.Linear(128, 9)
        
    def forward(self, x):
        x = self.pool1(torch.relu(self.conv1(x)))
        x = self.pool2(torch.relu(self.conv2(x)))
        x = torch.relu(self.conv3(x))
        x = torch.relu(self.conv4(x))
        x = x.reshape(-1, 64 * 7 * 7)
        x = torch.relu(self.fc1(x))
        x = self.fc2(x)
        return x
    
# Whole training process
def train_and_evaluate(model, train_loader, loss_criterion, optimizer, num_epoch, val_loader,scheduler, test_loader):
    # stop condition
    best_validation_loss = float('inf')
    # how many no_improvement the model can tolerate
    patience = 3
    improvement_threshold = 2
    
    train_accuracy_list = []
    val_accuracy_list = []
    train_loss_list = []
    val_loss_list = []
    for epoch_num in range(num_epoch):
        model.train()
        epoch_loss = 0.0
        for i, data in enumerate(train_loader):
            X, y = data
            optimizer.zero_grad()
            outputs = model(X)
            loss = loss_criterion(outputs, y)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
        scheduler.step()
        print(f'Epoch: {epoch_num + 1}, train_loss: {epoch_loss :.3f}')
        train_accuracy, train_loss = predict(model, train_loader, epoch_num, 'train', loss_criterion)
        val_accuracy, val_loss = predict(model, val_loader, epoch_num, 'val', loss_criterion)
        test_accuracy, test_loss = predict(model, test_loader, epoch_num, 'test', loss_criterion)
        print(f'Epoch: {epoch_num + 1}, val_loss: {val_loss :.3f}')
        print(f'Epoch: {epoch_num + 1}, test_loss: {test_loss :.3f}')
        train_accuracy_list.append(train_accuracy)
        val_accuracy_list.append(val_accuracy)
        train_loss_list.append(train_loss)
        val_loss_list.append(val_loss)
        if  best_validation_loss - val_loss > improvement_threshold:
            best_validation_loss = val_loss
            best_epoch = epoch_num
            # Count how many epochs have not improved the model since the best epoch, if it >= patience, the train process will stop early
            early_stopping_counter = 0
            # save the best model
            best_model_state_dict = copy.deepcopy(model.state_dict())
        else:
            early_stopping_counter += 1
        if early_stopping_counter >= patience:
            print(f'Best epoch: {best_epoch + 1}, finish')
            break
    model.load_state_dict(best_model_state_dict)
        
    return model, train_accuracy_list, val_accuracy_list, train_loss_list, val_loss_list

# model : The model after training, 
# loader: The dataset need to be predicted by the model
# epoch_num: The number of the current epoch. 
# type: used to clarify which dataset is being predicted : (train, test, val)
def predict(model, loader, epoch_num, type, loss_criterion):
    model.eval()
    correct = 0
    total = 0
    epoch_loss = 0
    with torch.no_grad():
        for i, samples in enumerate(loader):
            X, y = samples
            outputs = model(X)
            loss = loss_criterion(outputs, y)
            _, predicted = torch.max(outputs.data, axis = 1)
            total += y.size(0) 
            # train_loader is encoded for training, while others are not encoded. y is different in these three different datasets([1,0] in train_loader or [0] in others)
            correct += (predicted == y).sum().item()
            epoch_loss += loss
    # print(correct)
    print(f'Epoch: {epoch_num + 1}, Accuracy of the network on the {type} images: {100 * correct / total:.2f}%')
    return 100 * correct / total, epoch_loss

def get_confusion_matrix(model, X, y, lr):
    output = model(X)
    _, predict_y = torch.max(output.data, axis = 1)
    true_y = y
    # compute the confution matrix
    conf_matrix = confusion_matrix(true_y, predict_y)
    # compute the number of every classes, for the normalization of confusion matrix
    class_totals = conf_matrix.sum(axis=1, keepdims=True)
    # normalize the confusion matrix
    normalized_confusion_matrix = conf_matrix / class_totals
    
    # create images for confusion_matrix
    plt.figure(figsize=(8, 6))
    sns.heatmap(normalized_confusion_matrix, annot=True, fmt='.3f', cmap='Blues', xticklabels= np.arange(1,10,1), yticklabels= np.arange(1,10,1))
    plt.xlabel('Predicted Labels')
    plt.ylabel('True Labels')
    plt.title('Confusion Matrix')
    if(save_image == True):
        plt.savefig(f"C:/Users/xrw/Desktop/UCL/APPLIED MACHINE LEARNING/AMLS_I_assignment_kit/images/taskb/CNN3confusion{lr}.png")
    plt.show()
    
    
# plot train_loss and validation loss
def plot_metrics(train_losses, train_accuracies, test_losses, test_accuracies, lr, epoch_num):
    plt.figure(figsize=(14, 8))
    plt.subplot(1, 2, 1)
    plt.title(f'Loss:{lr}')
    plt.plot(train_losses, label='Train Loss')
    plt.plot(test_losses, label='Validation Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.legend()

    plt.subplot(1, 2, 2)
    plt.title(f'Accuracy:{lr}')
    plt.plot(train_accuracies, label='Train Accuracy')
    plt.plot(test_accuracies, label='Validation Accuracy')
    plt.xlabel('Epoch')
    plt.ylabel('Accuracy (%)')
    plt.legend()
    if(save_image == True):
        plt.savefig(f"C:/Users/xrw/Desktop/UCL/APPLIED MACHINE LEARNING/AMLS_I_assignment_kit/images/taskb/CNN3{lr}.png")
    plt.show()

# l2 regularization
def TaskB(data_set, model, lr, lr_decay, l2_lambda, lr_decay_rate, epoch_num):
    train_loader = data_set[0]
    val_loader = data_set[1]
    test_loader = data_set[2]
    test_tensor_X = data_set[3]
    test_tensor_y = data_set[4]
    # Use CrossEntropyLoss to train the model
    loss_criterion = nn.CrossEntropyLoss()

    # optimizer for the CNN
    optimizer = optim.Adam(model.parameters(), lr = lr, weight_decay = l2_lambda)

    # learning rate decay
    lr_decay_rate = 0.1
    scheduler = lr_scheduler.StepLR(optimizer, step_size=10, gamma=lr_decay_rate)

    model, train_accuracy, val_accuracy, train_loss, val_loss = train_and_evaluate(model, train_loader, loss_criterion, optimizer, epoch_num, val_loader, scheduler, test_loader)
    plot_metrics(train_loss, train_accuracy, val_loss, val_accuracy, lr, epoch_num)
    # After the model is trained, get the confusion matrix and recall
    get_confusion_matrix(model, test_tensor_X, test_tensor_y, lr)
    accuracy, test_loss = predict(model, test_loader, -1, 'test', loss_criterion)
    print('test accuracy: ', accuracy)
    print('loss: ', test_loss)
    return model, accuracy

# predict the testset using CNN 
def main_B(model_name, data_set, lr = 0.0001, lr_decay = False, l2_lambda = 0.02, lr_decay_rate = 0.1):
    best_accuracy = 0
    for i in range(0,3):
        if(model_name == 'CNN'):
            model, accuracy = TaskB(data_set, model = CNN(), l2_lambda=l2_lambda, lr = lr, lr_decay = lr_decay, lr_decay_rate = lr_decay_rate, epoch_num = 30)
        elif(model_name == 'CNN2'):
            model, accuracy = TaskB(data_set, model = CNN2(),l2_lambda=l2_lambda, lr = lr, lr_decay = lr_decay, lr_decay_rate = lr_decay_rate, epoch_num = 30)
        elif(model_name == 'CNN3'):
            model, accuracy = TaskB(data_set, model = CNN3(), l2_lambda=l2_lambda, lr = lr, lr_decay = lr_decay, lr_decay_rate = lr_decay_rate, epoch_num = 30)
        else:
            print("False name")
        if(accuracy > best_accuracy):
            best_accuracy = accuracy
            best_model = model
    print(f'{model_name}_best_accuracy: ', best_accuracy)
    # torch.save(best_model, f'{model_name}_best_model.pth')

# predict the testset using the saved model 
def main_read_B(model_dict_path, test_loader):
    model = torch.load(model_dict_path)
    predict(model, test_loader, 30, 'test', loss_criterion = nn.CrossEntropyLoss())