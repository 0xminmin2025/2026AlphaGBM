import { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';

export interface TaskStatus {
  id: string;
  task_type: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress_percent: number;
  current_step?: string;
  result_data?: any;
  error_message?: string;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
  related_history_id?: number;
  related_history_type?: string;
}

interface UseTaskPollingOptions {
  interval?: number; // Polling interval in ms, default 2000 (2 seconds)
  onTaskComplete?: (result: any) => void;
  onTaskError?: (error: string) => void;
  onTaskProgress?: (progress: number, step: string) => void;
}

export function useTaskPolling(options: UseTaskPollingOptions = {}) {
  const {
    interval = 2000,
    onTaskComplete,
    onTaskError,
    onTaskProgress
  } = options;

  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [pollError, setPollError] = useState<string>('');

  const startPolling = useCallback(async (taskId: string) => {
    setIsPolling(true);
    setPollError('');

    const poll = async () => {
      try {
        const response = await api.get(`/tasks/${taskId}/status`);
        const status: TaskStatus = response.data;

        setTaskStatus(status);

        // Call progress callback
        if (onTaskProgress && status.current_step) {
          onTaskProgress(status.progress_percent, status.current_step);
        }

        // Check if task is completed
        if (status.status === 'completed') {
          setIsPolling(false);

          // Fetch the full result
          try {
            const resultResponse = await api.get(`/tasks/${taskId}/result`);
            if (onTaskComplete) {
              onTaskComplete(resultResponse.data.result_data);
            }
          } catch (resultError: any) {
            console.error('Failed to fetch task result:', resultError);
            setPollError('Failed to fetch task result');
            if (onTaskError) {
              onTaskError('Failed to fetch task result');
            }
          }
          return;
        }

        // Check if task failed
        if (status.status === 'failed') {
          setIsPolling(false);
          const errorMsg = status.error_message || 'Task failed';
          setPollError(errorMsg);
          if (onTaskError) {
            onTaskError(errorMsg);
          }
          return;
        }

        // Continue polling if task is still pending or processing
        if (status.status === 'pending' || status.status === 'processing') {
          setTimeout(poll, interval);
        }

      } catch (error: any) {
        console.error('Polling error:', error);
        const errorMsg = error.response?.data?.error || 'Failed to check task status';
        setPollError(errorMsg);
        setIsPolling(false);
        if (onTaskError) {
          onTaskError(errorMsg);
        }
      }
    };

    // Start polling immediately
    poll();
  }, [interval, onTaskComplete, onTaskError, onTaskProgress]);

  const stopPolling = useCallback(() => {
    setIsPolling(false);
    setTaskStatus(null);
    setPollError('');
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      setIsPolling(false);
    };
  }, []);

  return {
    taskStatus,
    isPolling,
    pollError,
    startPolling,
    stopPolling
  };
}