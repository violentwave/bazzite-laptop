"use client";

import React from 'react';
import { ModelInfo } from '@/types/providers';

interface ModelsListProps {
  models?: ModelInfo[];
}

export function ModelsList({ models }: ModelsListProps) {
  if (!models || models.length === 0) {
    return (
      <div 
        className="text-center py-8 text-sm"
        aria-live="polite"
      >
        No models available
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {models.map((model) => (
        <div key={model.id} className="flex items-center gap-3 p-3 rounded border">
          <div className="flex-1">
            <div className="font-medium text-sm">{model.name}</div>
            <div className="text-xs text-muted-foreground">
              {model.provider} • {model.is_available ? 'Available' : 'Unavailable'}
            </div>
          </div>
          {model.is_available ? (
            <span className="h-2.5 w-2.5 bg-green-500 rounded-full"></span>
          ) : (
            <span className="h-2.5 w-2.5 bg-red-500 rounded-full"></span>
          )}
        </div>
      ))}
    </div>
  );
}