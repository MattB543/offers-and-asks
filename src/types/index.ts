// TypeScript types for EA Global Matching API responses

export interface AttendeeProfile {
  name: string
  company: string
  job_title: string
  country: string
  text: string
  similarity_score: number
  linkedin: string
  swapcard: string
  biography: string
}

export interface AttendeeInfo {
  name: string
  company: string
  job_title: string
  country: string
}

export interface MatchGroup {
  your_request: string
  matches: AttendeeProfile[]
}

export interface HelpGroup {
  your_offering: string
  matches: AttendeeProfile[]
}

export interface UsernameSearchResult {
  attendee: AttendeeInfo
  people_who_can_help_you: MatchGroup[]
  people_you_can_help: HelpGroup[]
}

export interface SimpleSearchResult {
  query: string
  matches: AttendeeProfile[]
}

export type SearchMode = 'username' | 'request' | 'offering'

export interface ErrorResponse {
  error: string
}
