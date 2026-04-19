import { useState, useEffect, useCallback, useRef } from 'react';

interface TaskEvent {
    type: string;
    task_id: string;
    [key: string]: any;
}

export function useWebSocket(url: string) {
    const [lastEvent, setLastEvent] = useState<TaskEvent | null>(null);
    const [connected, setConnected] = useState(false);
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        const ws = new WebSocket(url);
        wsRef.current = ws;

        ws.onopen = () => setConnected(true);

        ws.onmessage = (event) => {
            try {
                const parsed = JSON.parse(event.data);
                setLastEvent(parsed);
            } catch {}
        };

        ws.onclose = () => {
            setConnected(false);
            reconnectTimer.current = setTimeout(connect, 3000);
        };

        ws.onerror = () => ws.close();
    }, [url]);

    useEffect(() => {
        connect();
        return () => {
            clearTimeout(reconnectTimer.current);
            wsRef.current?.close();
        };
    }, [connect]);

    return { lastEvent, connected };
}
