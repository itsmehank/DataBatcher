'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

type UseCardDeleteModeResult = {
  deleteModeEntryId: string;
  deletingEntryId: string;
  softHint: string;
  startCardLongPress: (entryId: string, canDelete: boolean) => void;
  cancelCardLongPress: () => void;
  startDeleting: (entryId: string) => void;
  finishDeleting: () => void;
  clearDeleteMode: () => void;
};

export function useCardDeleteMode(): UseCardDeleteModeResult {
  const [deleteModeEntryId, setDeleteModeEntryId] = useState('');
  const [deletingEntryId, setDeletingEntryId] = useState('');
  const [softHint, setSoftHint] = useState('');

  const longPressTimer = useRef<number | null>(null);
  const deleteModeTimer = useRef<number | null>(null);
  const softHintTimer = useRef<number | null>(null);

  const clearDeleteMode = useCallback(() => {
    if (deleteModeTimer.current) {
      window.clearTimeout(deleteModeTimer.current);
      deleteModeTimer.current = null;
    }
    setDeleteModeEntryId('');
  }, []);

  const showSoftHintMessage = useCallback((message: string) => {
    setSoftHint(message);
    if (softHintTimer.current) {
      window.clearTimeout(softHintTimer.current);
    }
    softHintTimer.current = window.setTimeout(() => {
      setSoftHint('');
    }, 1800);
  }, []);

  const activateDeleteMode = useCallback((entryId: string) => {
    setDeleteModeEntryId(entryId);
    if (deleteModeTimer.current) {
      window.clearTimeout(deleteModeTimer.current);
    }
    deleteModeTimer.current = window.setTimeout(() => {
      setDeleteModeEntryId('');
    }, 3000);
  }, []);

  const startCardLongPress = useCallback(
    (entryId: string, canDelete: boolean) => {
      if (longPressTimer.current) {
        window.clearTimeout(longPressTimer.current);
      }

      longPressTimer.current = window.setTimeout(() => {
        if (canDelete) {
          activateDeleteMode(entryId);
        } else {
          showSoftHintMessage('본인 기록만 삭제할 수 있어요.');
        }
      }, 600);
    },
    [activateDeleteMode, showSoftHintMessage],
  );

  const cancelCardLongPress = useCallback(() => {
    if (longPressTimer.current) {
      window.clearTimeout(longPressTimer.current);
      longPressTimer.current = null;
    }
  }, []);

  const startDeleting = useCallback((entryId: string) => {
    setDeletingEntryId(entryId);
  }, []);

  const finishDeleting = useCallback(() => {
    setDeletingEntryId('');
  }, []);

  useEffect(() => {
    function onCloseDeleteMode(event: PointerEvent) {
      const target = event.target as HTMLElement | null;
      if (target && !target.closest('.card')) {
        clearDeleteMode();
      }
    }

    function onEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        clearDeleteMode();
      }
    }

    window.addEventListener('pointerdown', onCloseDeleteMode);
    window.addEventListener('keydown', onEscape);
    return () => {
      window.removeEventListener('pointerdown', onCloseDeleteMode);
      window.removeEventListener('keydown', onEscape);
    };
  }, [clearDeleteMode]);

  useEffect(() => {
    return () => {
      if (longPressTimer.current) {
        window.clearTimeout(longPressTimer.current);
      }
      if (deleteModeTimer.current) {
        window.clearTimeout(deleteModeTimer.current);
      }
      if (softHintTimer.current) {
        window.clearTimeout(softHintTimer.current);
      }
    };
  }, []);

  return {
    deleteModeEntryId,
    deletingEntryId,
    softHint,
    startCardLongPress,
    cancelCardLongPress,
    startDeleting,
    finishDeleting,
    clearDeleteMode,
  };
}
