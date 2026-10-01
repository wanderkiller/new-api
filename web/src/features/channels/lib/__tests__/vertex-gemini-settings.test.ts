/*
Copyright (C) 2023-2026 QuantumNous

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.

For commercial licensing, please contact support@quantumnous.com
*/
import { describe, expect, test } from 'vitest'

import { channelSchema } from '../../types'
import {
  CHANNEL_FORM_DEFAULT_VALUES,
  transformChannelToFormDefaults,
  transformFormDataToUpdatePayload,
} from '../channel-form'

describe('Vertex Gemini OpenAI compatibility setting', () => {
  test.each([true, false])(
    'editing a Vertex channel preserves enabled=%s',
    (enabled) => {
      const channel = channelSchema.parse({
        id: 3,
        key: '',
        created_time: 0,
        test_time: 0,
        response_time: 0,
        balance_updated_time: 0,
        name: 'Vertex',
        type: 41,
        status: 1,
        models: 'gemini-3.8-flash',
        group: 'default',
        settings: JSON.stringify({
          vertex_key_type: 'json',
          vertex_gemini_openai_compat_enabled: enabled,
        }),
      })
      const form = transformChannelToFormDefaults(channel)
      const payload = transformFormDataToUpdatePayload(form, channel.id)
      expect(JSON.parse(payload.settings ?? '{}')).toMatchObject({
        vertex_key_type: 'json',
        vertex_gemini_openai_compat_enabled: enabled,
      })
    }
  )

  test('changing from Vertex to OpenAI removes Vertex-only settings', () => {
    const form = {
      ...CHANNEL_FORM_DEFAULT_VALUES,
      type: 1,
      vertex_gemini_openai_compat_enabled: true,
      settings:
        '{"vertex_key_type":"json","vertex_gemini_openai_compat_enabled":true}',
    }
    const payload = transformFormDataToUpdatePayload(form, 3)
    expect(JSON.parse(payload.settings ?? '{}')).not.toHaveProperty(
      'vertex_gemini_openai_compat_enabled'
    )
    expect(JSON.parse(payload.settings ?? '{}')).not.toHaveProperty(
      'vertex_key_type'
    )
  })
})
