
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Bidirectional, BatchNormalization
import numpy as np

class DeepQuantModel:
    """
    Implements the 'Comprehensive Deep Learning System' (Shen et al. 2020).
    Core: Bidirectional LSTM to capture temporal dependencies (Trends/Cycles).
    """
    
    def __init__(self, input_shape):
        """
        input_shape: (time_steps, features)
        """
        self.input_shape = input_shape
        self.model = self._build_model()
        
    def _build_model(self):
        model = Sequential()
        
        # FIX: Explicit Input Layer to silence Keras 3.x warning
        model.add(tf.keras.Input(shape=self.input_shape))
        
        # 1. Feature Extraction Layer (LSTM)
        # Bidirectional allows the model to see past and future contexts within the window
        model.add(Bidirectional(LSTM(128, return_sequences=True)))
        model.add(Dropout(0.3)) # Prevent overfitting
        model.add(BatchNormalization()) # Stabilize training
        
        # 2. Deep Temporal Layer
        model.add(LSTM(64, return_sequences=False))
        model.add(Dropout(0.3))
        
        # 3. Decision Layer (Dense)
        model.add(Dense(32, activation='relu'))
        
        # Output: Probability of "Profitable Signal"
        model.add(Dense(1, activation='sigmoid'))
        
        optimizer = tf.keras.optimizers.Adam(learning_rate=0.001)
        
        model.compile(
            optimizer=optimizer,
            loss='binary_crossentropy',
            metrics=['accuracy', tf.keras.metrics.AUC(name='auc')]
        )
        
        return model
        
    def summary(self):
        return self.model.summary()
        
    def fit(self, X_train, y_train, X_val, y_val, epochs=50, batch_size=32, callbacks=None, verbose=1):
        # Use Early Stopping
        es_callback = tf.keras.callbacks.EarlyStopping(
            monitor='val_auc', patience=10, restore_best_weights=True, mode='max'
        )
        
        final_callbacks = [es_callback]
        if callbacks:
            final_callbacks.extend(callbacks)
        
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=final_callbacks,
            verbose=verbose
        )
        return history
    
    def predict(self, X):
        return self.model.predict(X)
    
    def save(self, path):
        self.model.save(path)
        
    @staticmethod
    def load(path):
        return tf.keras.models.load_model(path)
