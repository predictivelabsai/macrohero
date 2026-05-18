import { describe, expect, it, vi, beforeEach } from "vitest";
import { runFactorProjection } from "../../src/analytics/run-factor-projection.js";

const HAPPY_PATH_RESPONSE = {
  pair: "EUR/USD",
  horizon_days: 14,
  regression_window_days: 252,
  r_squared: 0.42,
  intercept: 0.0001,
  factors: [
    {
      name: "Brent crude",
      ticker: "BNO",
      beta: -0.15,
      expected_change: -7.5,
      unit: "%",
      contribution_pct: 1.125,
      se: 0.05,
      t_stat: -3.0,
      p_value: 0.003,
      ci_low: -0.25,
      ci_high: -0.05,
      vif: 1.1,
      severity: "severe",
      direction: "down",
      sigma_multiple: -2.0,
    },
  ],
  projection: {
    point_pct: 1.125,
    band_95_low_pct: -0.5,
    band_95_high_pct: 2.75,
    spot_at_t0: 1.05,
    projected_spot: 1.062,
    spot_band_low: 1.044,
    spot_band_high: 1.079,
    residual_variance_pct2: 1.2,
    parameter_variance_pct2: 0.3,
  },
  diagnostics: {
    n_observations: 252,
    warnings: [],
    error: null,
  },
};

describe("runFactorProjection tool", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts the args body to ${NUMERICS_URL}/v1/projection", async () => {
    const fetchSpy = vi.fn<typeof fetch>(async () =>
      new Response(JSON.stringify(HAPPY_PATH_RESPONSE), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchSpy);
    vi.stubEnv("NUMERICS_URL", "http://numerics-test:8001");

    await runFactorProjection.invoke({
      pair: "EUR/USD",
      horizon_days: 14,
      factors: [{ name: "Brent crude", direction: "down", severity: "severe" }],
    });

    expect(fetchSpy).toHaveBeenCalledOnce();
    const [url, init] = fetchSpy.mock.calls[0]!;
    expect(url).toBe("http://numerics-test:8001/v1/projection");
    expect(init?.method).toBe("POST");
    expect(init?.headers).toMatchObject({ "content-type": "application/json" });
    const body = JSON.parse(init?.body as string);
    expect(body).toEqual({
      pair: "EUR/USD",
      horizon_days: 14,
      factors: [{ name: "Brent crude", direction: "down", severity: "severe" }],
      regression_window_days: 252,
    });
  });

  it("returns the parsed projection result on 200", async () => {
    vi.stubGlobal("fetch", async () =>
      new Response(JSON.stringify(HAPPY_PATH_RESPONSE), { status: 200 }),
    );
    const result = await runFactorProjection.invoke({
      pair: "EUR/USD",
      horizon_days: 14,
      factors: [{ name: "Brent crude", direction: "down", severity: "severe" }],
    });
    expect(result).toMatchObject({
      pair: "EUR/USD",
      r_squared: 0.42,
      diagnostics: { error: null },
    });
  });

  it("returns an error envelope on non-200 instead of throwing", async () => {
    vi.stubGlobal("fetch", async () =>
      new Response("internal error", { status: 500 }),
    );
    const result = await runFactorProjection.invoke({
      pair: "EUR/USD",
      horizon_days: 14,
      factors: [{ name: "Brent crude", direction: "down", severity: "severe" }],
    });
    expect(result).toMatchObject({
      pair: "EUR/USD",
      horizon_days: 14,
      projection: null,
      diagnostics: {
        error: {
          code: "numerics_http_error",
          message: expect.stringContaining("500"),
        },
      },
    });
  });

  it("returns an error envelope on network failure instead of throwing", async () => {
    vi.stubGlobal("fetch", async () => {
      throw new Error("ECONNREFUSED");
    });
    const result = await runFactorProjection.invoke({
      pair: "EUR/USD",
      horizon_days: 14,
      factors: [{ name: "Brent crude", direction: "down", severity: "severe" }],
    });
    expect(result.projection).toBeNull();
    expect(result.diagnostics.error?.code).toBe("numerics_network_error");
  });

  it("rejects an unknown factor name at the Zod boundary", async () => {
    vi.stubGlobal("fetch", async () =>
      new Response(JSON.stringify(HAPPY_PATH_RESPONSE), { status: 200 }),
    );
    await expect(
      runFactorProjection.invoke({
        pair: "EUR/USD",
        horizon_days: 14,
        // @ts-expect-error - intentionally bad value
        factors: [{ name: "Not a factor", direction: "down", severity: "severe" }],
      }),
    ).rejects.toThrow(/Invalid enum value|Invalid input/);
  });
});
