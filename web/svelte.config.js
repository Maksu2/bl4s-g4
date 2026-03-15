import adapter from '@sveltejs/adapter-node';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	kit: {
		// Using adapter-node for production deployment in Docker/HA OS
		adapter: adapter({
			out: 'build'
		})
	}
};

export default config;
