/// <reference types="next" />
/// <reference types="next/types/global" />

import { NextRequest, NextResponse } from 'next/server';
import { v4 as uuidv4 } from 'uuid';

// Configuration
const MAX_BATCH_SIZE = 10;
const BATCH_TIMEOUT = 1000; // 1 second
const MAX_RETRIES = 3;

interface BatchItem {
  id: string;
  request: Request;
  timestamp: number;
  resolve: (value: Response) => void;
  reject: (reason: any) => void;
}

interface BatchResult {
  id: string;
  response?: Response;
  error?: any;
}

export class BatchProcessor {
  private queue: BatchItem[] = [];
  private processing = false;
  private timer: ReturnType<typeof setTimeout> | null = null;

  async processRequest(request: Request): Promise<Response> {
    return this.add(request);
  }

  private async add(request: Request): Promise<Response> {
    return new Promise<Response>((resolve, reject) => {
      const item: BatchItem = {
        id: uuidv4(),
        request,
        timestamp: Date.now(),
        resolve,
        reject,
      };

      this.queue.push(item);
      this.scheduleProcessing();

      // Set timeout for individual request
      setTimeout(() => {
        const index = this.queue.findIndex(i => i.id === item.id);
        if (index !== -1) {
          this.queue.splice(index, 1);
          reject(new Error('Request timeout'));
        }
      }, BATCH_TIMEOUT * 2);
    });
  }

  private scheduleProcessing() {
    if (this.timer) {
      clearTimeout(this.timer);
    }

    this.timer = setTimeout(() => {
      this.processBatch();
    }, BATCH_TIMEOUT);
  }

  private async processBatch() {
    if (this.processing || this.queue.length === 0) {
      return;
    }

    this.processing = true;
    const batch = this.queue.splice(0, MAX_BATCH_SIZE);

    try {
      // Process batch in parallel
      const results = await Promise.all<BatchResult>(
        batch.map(async (item) => {
          try {
            const response = await fetch(item.request);
            return { id: item.id, response };
          } catch (error) {
            return { id: item.id, error };
          }
        })
      );

      // Resolve or reject each promise
      results.forEach((result) => {
        const item = batch.find(i => i.id === result.id);
        if (item) {
          if (result.response) {
            item.resolve(result.response);
          } else {
            item.reject(result.error || new Error('Unknown error'));
          }
        }
      });
    } catch (error) {
      // If batch processing fails, reject all items
      batch.forEach(item => item.reject(error));
    } finally {
      this.processing = false;
      if (this.queue.length > 0) {
        this.scheduleProcessing();
      }
    }
  }
}

// Type definitions for Next.js
declare global {
  interface Window {
    fetch: typeof fetch;
  }
}

const batchProcessor = new BatchProcessor();

export async function POST(request: NextRequest): Promise<NextResponse> {
  try {
    // Clone the request to avoid consuming the body
    const clonedRequest = request.clone();
    const response = await batchProcessor.processRequest(clonedRequest);
    return NextResponse.json({ success: true, data: await response.json() });
  } catch (error) {
    console.error('Error processing request:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
} 