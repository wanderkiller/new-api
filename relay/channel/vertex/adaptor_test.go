package vertex

import (
	"bytes"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"

	relaycommon "github.com/QuantumNous/new-api/relay/common"
	"github.com/QuantumNous/new-api/relaykit/dto"
	"github.com/QuantumNous/new-api/relaykit/types"
	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestAdaptorInitGeminiOpenAICompatibilityRouting(t *testing.T) {
	// Since the rc.31 relay-conversion refactor, thinking/effort model-name
	// modifiers are stripped by helper.ApplyReasoningModelSuffix (relay entry
	// layer) before Adaptor.Init ever runs: it normalizes UpstreamModelName to
	// the bare base and records the modifier on info.ReasoningConversion
	// instead. So a "thinking suffix" case is simulated with the base model
	// name plus a populated ReasoningConversion, not a suffixed model string.
	budget := 1024
	tests := []struct {
		name                string
		model               string
		enabled             bool
		reasoningConversion *dto.ReasoningConversionState
		requestMode         int
	}{
		{name: "Gemini defaults to native", model: "gemini-3.7-flash", requestMode: RequestModeGemini},
		{name: "Gemini opt-in uses OpenAI compatibility", model: "gemini-3.7-flash", enabled: true, requestMode: RequestModeOpenSource},
		{name: "Google-prefixed Gemini opt-in uses OpenAI compatibility", model: "google/gemini-3.7-flash", enabled: true, requestMode: RequestModeOpenSource},
		{name: "Gemini thinking modifier stays native", model: "gemini-3.7-flash", enabled: true, reasoningConversion: &dto.ReasoningConversionState{Mode: "enabled", BudgetTokens: &budget}, requestMode: RequestModeGemini},
		{name: "Gemini effort modifier stays native", model: "gemini-3.7-flash", enabled: true, reasoningConversion: &dto.ReasoningConversionState{Effort: "high"}, requestMode: RequestModeGemini},
		{name: "Imagen stays native", model: "imagen-4.0-generate-001", enabled: true, requestMode: RequestModeGemini},
		{name: "Claude remains Claude", model: "claude-sonnet-4", enabled: true, requestMode: RequestModeClaude},
		{name: "Llama remains OpenAI compatibility", model: "meta-llama-3-70b-instruct", enabled: true, requestMode: RequestModeOpenSource},
		{name: "MaaS remains OpenAI compatibility", model: "qwen2.5-72b-maas", enabled: true, requestMode: RequestModeOpenSource},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			adaptor := &Adaptor{}
			adaptor.Init(&relaycommon.RelayInfo{
				ReasoningConversion: tt.reasoningConversion,
				ChannelMeta: &relaycommon.ChannelMeta{
					UpstreamModelName: tt.model,
					ChannelOtherSettings: dto.ChannelOtherSettings{
						VertexGeminiOpenAICompatEnabled: tt.enabled,
					},
				},
			})

			assert.Equal(t, tt.requestMode, adaptor.RequestMode)
		})
	}
}

func TestConvertOpenAIRequestGeminiOpenAICompatibilityPrefixesModel(t *testing.T) {
	tests := []struct {
		name          string
		upstreamModel string
		requestModel  string
		expectedModel string
	}{
		{name: "Gemini", upstreamModel: "gemini-3.7-flash", requestModel: "customer-gemini", expectedModel: "google/gemini-3.7-flash"},
		{name: "already prefixed Gemini", upstreamModel: "google/gemini-3.7-flash", requestModel: "customer-gemini", expectedModel: "google/gemini-3.7-flash"},
		{name: "Llama stays unchanged", upstreamModel: "meta-llama-3-70b-instruct", requestModel: "meta-llama-3-70b-instruct", expectedModel: "meta-llama-3-70b-instruct"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			request := &dto.GeneralOpenAIRequest{Model: tt.requestModel}
			info := &relaycommon.RelayInfo{ChannelMeta: &relaycommon.ChannelMeta{
				UpstreamModelName: tt.upstreamModel,
				ChannelOtherSettings: dto.ChannelOtherSettings{
					VertexGeminiOpenAICompatEnabled: true,
				},
			}}
			adaptor := &Adaptor{}
			adaptor.Init(info)

			convertedValue, err := adaptor.ConvertOpenAIRequest(nil, info, request)
			require.NoError(t, err)
			converted, ok := convertedValue.(*dto.GeneralOpenAIRequest)
			require.True(t, ok)
			assert.Same(t, request, converted)
			assert.Equal(t, tt.expectedModel, converted.Model)
		})
	}
}

func TestGeminiOpenAICompatibilityPreservesThoughtSignatureResponse(t *testing.T) {
	const upstreamResponse = `{"id":"chatcmpl-1","object":"chat.completion","created":1,"model":"google/gemini-3.7-flash","choices":[{"index":0,"message":{"role":"assistant","tool_calls":[{"id":"call_1","type":"function","function":{"name":"get_current_time","arguments":"{}"},"extra_content":{"google":{"thought_signature":"signature-value"}}}]},"finish_reason":"tool_calls"}],"usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2}}`

	recorder := httptest.NewRecorder()
	context, _ := gin.CreateTestContext(recorder)
	info := &relaycommon.RelayInfo{
		RelayFormat: types.RelayFormatOpenAI,
		ChannelMeta: &relaycommon.ChannelMeta{
			UpstreamModelName: "gemini-3.7-flash",
			ChannelOtherSettings: dto.ChannelOtherSettings{
				VertexGeminiOpenAICompatEnabled: true,
			},
		},
	}
	adaptor := &Adaptor{}
	adaptor.Init(info)

	_, apiErr := adaptor.DoResponse(context, &http.Response{
		StatusCode: http.StatusOK,
		Header:     http.Header{"Content-Type": []string{"application/json"}},
		Body:       io.NopCloser(bytes.NewBufferString(upstreamResponse)),
	}, info)
	require.Nil(t, apiErr)
	assert.Equal(t, upstreamResponse, recorder.Body.String())
}
