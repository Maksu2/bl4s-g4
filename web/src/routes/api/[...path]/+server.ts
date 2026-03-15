import type { RequestHandler } from './$types';

const API_URL = 'http://localhost:8000';

export const GET: RequestHandler = async ({ params, request, url }) => {
    const path = params.path || '';
    const targetUrl = `${API_URL}/${path}${url.search}`;

    const response = await fetch(targetUrl, {
        headers: {
            'Content-Type': 'application/json',
        },
    });

    return new Response(response.body, {
        status: response.status,
        headers: response.headers,
    });
};

export const POST: RequestHandler = async ({ params, request, url }) => {
    const path = params.path || '';
    const targetUrl = `${API_URL}/${path}${url.search}`;

    const response = await fetch(targetUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: await request.text(),
    });

    return new Response(response.body, {
        status: response.status,
        headers: response.headers,
    });
};

export const DELETE: RequestHandler = async ({ params, request }) => {
    const path = params.path || '';
    const response = await fetch(`${API_URL}/${path}`, {
        method: 'DELETE',
    });

    return new Response(response.body, {
        status: response.status,
        headers: response.headers,
    });
};
