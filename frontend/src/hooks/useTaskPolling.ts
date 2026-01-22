import { useState, useEffect, useCallback, useRef } from 'react';
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
  timeout?: number; // Timeout in ms, default 300000 (5 minutes)
  maxRetries?: number; // Max consecutive errors before giving up, default 3
  onTaskComplete?: (result: any) => void;
  onTaskError?: (error: string) => void;
  onTaskProgress?: (progress: number, step: string) => void;
  onTaskTimeout?: () => void;
}

export function useTaskPolling(options: UseTaskPollingOptions = {}) {
  const {
    interval = 2000,
    timeout = 300000, // 5 minutes default
    maxRetries = 3,
    onTaskComplete,
    onTaskError,
    onTaskProgress,
    onTaskTimeout
  } = options;

  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [pollError, setPollError] = useState<string>('');

  // Refs for tracking state across poll cycles
  const startTimeRef = useRef<number | null>(null);
  const pollTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const retryCountRef = useRef<number>(0);
  const isPollingRef = useRef<boolean>(false);

  const clearPollTimeout = useCallback(() => {
    if (pollTimeoutRef.current) {
      clearTimeout(pollTimeoutRef.current);
      pollTimeoutRef.current = null;
    }
  }, []);

  const startPolling = useCallback(async (taskId: string) => {
    // Reset state
    setIsPolling(true);
    isPollingRef.current = true;
    setPollError('');
    startTimeRef.current = Date.now();
    retryCountRef.current = 0;

    const poll = async () => {
      // Check if polling was stopped
      if (!isPollingRef.current) {
        return;
      }

      // Check for timeout
      if (startTimeRef.current && Date.now() - startTimeRef.current > timeout) {
        setIsPolling(false);
        isPollingRef.current = false;
        const timeoutMsg = 'Analysis timeout. The request took too long to complete.';
        setPollError(timeoutMsg);
        if (onTaskTimeout) {
          onTaskTimeout();
        } else if (onTaskError) {
          onTaskError(timeoutMsg);
        }
        return;
      }

      try {
        const response = await api.get(`/tasks/${taskId}/status`);
        const status: TaskStatus = response.data;

        // Reset retry count on successful request
        retryCountRef.current = 0;
        setTaskStatus(status);

        // Call progress callback
        if (onTaskProgress && status.current_step) {
          onTaskProgress(status.progress_percent, status.current_step);
        }

        // Check if task is completed
        if (status.status === 'completed') {
          setIsPolling(false);
          isPollingRef.current = false;

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
          isPollingRef.current = false;
          const errorMsg = status.error_message || 'Task failed';
          setPollError(errorMsg);
          if (onTaskError) {
            onTaskError(errorMsg);
          }
          return;
        }

        // Continue polling if task is still pending or processing
        if (status.status === 'pending' || status.status === 'processing') {
          pollTimeoutRef.current = setTimeout(poll, interval);
        }

      } catch (error: any) {
        console.error('Polling error:', error);
        retryCountRef.current += 1;

        // Check if max retries exceeded
        if (retryCountRef.current >= maxRetries) {
          const errorMsg = error.response?.data?.error || 'Failed to check task status after multiple attempts';
          setPollError(errorMsg);
          setIsPolling(false);
          isPollingRef.current = false;
          if (onTaskError) {
            onTaskError(errorMsg);
          }
          return;
        }

        // Exponential backoff for retries
        const backoffDelay = interval * Math.pow(2, Math.min(retryCountRef.current - 1, 3));
        console.log(`Retrying in ${backoffDelay}ms (attempt ${retryCountRef.current}/${maxRetries})`);
        pollTimeoutRef.current = setTimeout(poll, backoffDelay);
      }
    };

    // Start polling immediately
    poll();
  }, [interval, timeout, maxRetries, onTaskComplete, onTaskError, onTaskProgress, onTaskTimeout]);

  const stopPolling = useCallback(() => {
    setIsPolling(false);
    isPollingRef.current = false;
    setTaskStatus(null);
    setPollError('');
    clearPollTimeout();
    startTimeRef.current = null;
    retryCountRef.current = 0;
  }, [clearPollTimeout]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isPollingRef.current = false;
      clearPollTimeout();
    };
  }, [clearPollTimeout]);

  // Calculate elapsed time for UI display
  const getElapsedTime = useCallback(() => {
    if (!startTimeRef.current) return 0;
    return Date.now() - startTimeRef.current;
  }, []);

  // Calculate remaining time before timeout
  const getRemainingTime = useCallback(() => {
    if (!startTimeRef.current) return timeout;
    const elapsed = Date.now() - startTimeRef.current;
    return Math.max(0, timeout - elapsed);
  }, [timeout]);

  return {
    taskStatus,
    isPolling,
    pollError,
    startPolling,
    stopPolling,
    getElapsedTime,
    getRemainingTime
  };
}